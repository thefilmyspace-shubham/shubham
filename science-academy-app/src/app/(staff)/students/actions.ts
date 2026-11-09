"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { canSeeStudent, requirePermission, requireStaff } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { ensureParentUser } from "@/lib/notify";
import { readFile, saveFile } from "@/lib/storage";
import { checkMarksheet } from "@/lib/ai/marksheet";
import { monthStart, todayIst } from "@/lib/format";
import {
  CONSENT_VERSION,
  getStudent,
  parseRegistration,
  recordIdChange,
  type FieldErrors,
  type ParsedRegistration,
} from "@/lib/students";
import type { Batch, Marksheet, Student } from "@/lib/types";

export type SaveState = { errors?: FieldErrors; message?: string } | null;

const MAX_FILE = 10 * 1024 * 1024;
const FILE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"];

/** Register (or save as draft, or save edits to) a student. */
export async function saveStudent(_prev: SaveState, form: FormData): Promise<SaveState> {
  const viewer = await requirePermission("students.edit");
  const intent = form.get("intent") === "register" ? "register" : "draft";
  const existingId = String(form.get("student_id") ?? "");
  const existing = existingId ? await getStudent(existingId) : null;
  if (existingId && !existing) return { message: "Student not found." };
  const alreadyRegistered = existing !== null && existing.status !== "draft";
  // Editing a registered student is always strict.
  const parsed = parseRegistration(form, alreadyRegistered ? "register" : intent);
  if (!parsed.ok) return { errors: parsed.errors, message: "Please fix the marked fields." };
  const data = parsed.data;

  // Marksheet files: check type and size before anything is saved.
  for (const i of [0, 1]) {
    const file = form.get(`ms${i}_file`);
    if (file instanceof File && file.size > 0) {
      if (file.size > MAX_FILE) return { errors: { [`ms${i}_file`]: "File is larger than 10 MB." }, message: "Please fix the marked fields." };
      if (file.type && !FILE_TYPES.includes(file.type)) {
        return { errors: { [`ms${i}_file`]: "Upload a photo (JPG, PNG) or a PDF." }, message: "Please fix the marked fields." };
      }
    }
  }

  const db = adminClient();
  if (data.student.batch_id) {
    const { data: batch } = await db.from("batches").select("*").eq("id", data.student.batch_id).maybeSingle<Batch>();
    if (!batch || batch.board !== data.student.board || batch.class !== data.student.current_class) {
      return { errors: { batch_id: "This batch is not for the chosen board and class." }, message: "Please fix the marked fields." };
    }
  }

  // 1. Save the student row (as a draft until Register).
  const fields = { ...data.student, updated_at: new Date().toISOString() };
  let student: Student;
  if (existing) {
    const { data: row, error } = await db.from("students").update(fields).eq("id", existing.id).select("*").single<Student>();
    if (error || !row) return { message: "Could not save. Please try again." };
    student = row;
  } else {
    const { data: row, error } = await db
      .from("students")
      .insert({ ...fields, status: "draft", created_by: viewer.user.id })
      .select("*")
      .single<Student>();
    if (error || !row) return { message: "Could not save. Please try again." };
    student = row;
  }

  // 2. Contact numbers (one login number).
  await saveGuardians(student.id, data);

  // 3. Marksheets (upload + AI check).
  await saveMarksheets(student, form);

  // 4. Consent.
  if (data.consent && data.consentBy) {
    const { count } = await db.from("consents").select("id", { count: "exact", head: true }).eq("student_id", student.id);
    if (!count) {
      await db.from("consents").insert({
        student_id: student.id,
        text_version: CONSENT_VERSION,
        given_by: data.consentBy,
        recorded_by: viewer.user.id,
      });
    }
  }

  // 5. Register: the roll number is made now, never before.
  if (!alreadyRegistered && intent === "register") {
    const { data: roll, error } = await db.rpc("allocate_roll");
    if (error || typeof roll !== "number") return { message: "Could not create the roll number. Please try again." };
    const { data: row, error: regError } = await db
      .from("students")
      .update({ roll_number: roll, status: "active", admission_session: student.session_year })
      .eq("id", student.id)
      .select("*")
      .single<Student>();
    if (regError || !row) return { message: "Could not register. Please try again." };
    student = row;
    await recordIdChange(student);
    await afterRegister(student, data);
    await logActivity(viewer, "student.register", { type: "student", id: student.id }, { code: student.code, name: student.name });
    revalidatePath("/students");
    redirect(`/students/${student.id}?registered=1`);
  }

  if (alreadyRegistered && existing) {
    // A corrected board/class/session changes the ID; the roll stays.
    if (
      existing.board !== student.board ||
      existing.current_class !== student.current_class ||
      existing.session_year !== student.session_year
    ) {
      await recordIdChange(student);
    }
    if (Number(existing.monthly_fee) !== Number(student.monthly_fee)) {
      await db
        .from("fees_ledger")
        .update({ amount: student.monthly_fee })
        .eq("student_id", student.id)
        .eq("month", monthStart(todayIst()));
    }
    const login = data.guardians.find((g) => g.relation === data.loginRelation);
    if (login) await ensureParentUser(login.mobile, login.name ?? "Parent");
    await logActivity(viewer, "student.edit", { type: "student", id: student.id }, { code: student.code, name: student.name });
    revalidatePath(`/students/${student.id}`);
    redirect(`/students/${student.id}?saved=1`);
  }

  await logActivity(viewer, "student.draft", { type: "student", id: student.id }, { name: student.name });
  revalidatePath("/students");
  redirect(`/students/${student.id}/edit?draft=1`);
}

async function saveGuardians(studentId: string, data: ParsedRegistration) {
  const db = adminClient();
  await db.from("guardians").delete().eq("student_id", studentId);
  if (!data.guardians.length) return;
  await db.from("guardians").insert(
    data.guardians.map((g) => ({
      student_id: studentId,
      relation: g.relation,
      name: g.name,
      mobile: g.mobile,
      is_login_number: g.relation === data.loginRelation,
    })),
  );
}

async function afterRegister(student: Student, data: ParsedRegistration) {
  const db = adminClient();
  const login = data.guardians.find((g) => g.relation === data.loginRelation);
  if (login) await ensureParentUser(login.mobile, login.name ?? "Parent");
  if (Number(student.monthly_fee) > 0) {
    await db
      .from("fees_ledger")
      .upsert(
        { student_id: student.id, month: monthStart(todayIst()), amount: student.monthly_fee },
        { onConflict: "student_id,month", ignoreDuplicates: true },
      );
  }
}

/** Two marksheet slots: ms{0,1}_id, ms{0,1}_year, ms{0,1}_pct, ms{0,1}_file. */
async function saveMarksheets(student: Student, form: FormData) {
  const jobs: Promise<unknown>[] = [];
  for (const i of [0, 1]) {
    const id = String(form.get(`ms${i}_id`) ?? "");
    const year = String(form.get(`ms${i}_year`) ?? "").trim();
    const pctRaw = String(form.get(`ms${i}_pct`) ?? "").trim();
    const pct = pctRaw === "" ? null : Number(pctRaw);
    const typedPct = pct !== null && Number.isFinite(pct) && pct >= 0 && pct <= 100 ? pct : null;
    const file = form.get(`ms${i}_file`);
    const hasFile = file instanceof File && file.size > 0;
    if (!id && !hasFile && !year && typedPct === null) continue;
    jobs.push(saveOneMarksheet(student, { id: id || null, year: year || `Marksheet ${i + 1}`, typedPct, file: hasFile ? (file as File) : null }));
  }
  await Promise.all(jobs);
}

async function saveOneMarksheet(
  student: Student,
  slot: { id: string | null; year: string; typedPct: number | null; file: File | null },
) {
  const db = adminClient();
  let current: Marksheet | null = null;
  if (slot.id) {
    const { data } = await db.from("marksheets").select("*").eq("id", slot.id).eq("student_id", student.id).maybeSingle<Marksheet>();
    current = data ?? null;
  }
  let filePath = current?.file_path ?? null;
  let fileName = current?.file_name ?? null;
  let bytes: Buffer | null = null;
  let mime = "";
  if (slot.file) {
    bytes = Buffer.from(await slot.file.arrayBuffer());
    mime = slot.file.type || guessMime(slot.file.name);
    filePath = await saveFile("marksheets", student.id, { name: slot.file.name, type: mime, data: bytes });
    fileName = slot.file.name;
  }
  const needsCheck =
    Boolean(slot.file) ||
    (current !== null &&
      (Number(current.typed_percentage) !== Number(slot.typedPct) || current.ai_check_result === "pending") &&
      Boolean(filePath));
  let check: Pick<Marksheet, "ai_check_result" | "ai_read_name" | "ai_read_percentage" | "ai_note"> | null = null;
  if (needsCheck && filePath) {
    if (!bytes) {
      bytes = await readFile("marksheets", filePath);
      mime = guessMime(fileName ?? filePath);
    }
    if (bytes) {
      const r = await checkMarksheet({ data: bytes, mimeType: mime, typedName: student.name, typedPercentage: slot.typedPct });
      check = { ai_check_result: r.result, ai_read_name: r.readName, ai_read_percentage: r.readPercentage, ai_note: r.note };
    }
  }
  if (!filePath && !check) {
    check = { ai_check_result: "pending", ai_read_name: null, ai_read_percentage: null, ai_note: "No marksheet file uploaded yet." };
  }
  const row = {
    student_id: student.id,
    year_label: slot.year,
    file_path: filePath,
    file_name: fileName,
    typed_percentage: slot.typedPct,
    ...(check ?? {}),
  };
  if (current) await db.from("marksheets").update(row).eq("id", current.id);
  else await db.from("marksheets").insert(row);
}

function guessMime(name: string): string {
  const ext = name.toLowerCase().split(".").pop();
  return (
    { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", heic: "image/heic", pdf: "application/pdf" }[ext ?? ""] ??
    "application/octet-stream"
  );
}

/** Run the AI check again on a saved marksheet (after a better photo or a typo fix). */
export async function recheckMarksheet(form: FormData) {
  await requirePermission("students.edit");
  const id = String(form.get("marksheet_id") ?? "");
  const db = adminClient();
  const { data: ms } = await db.from("marksheets").select("*").eq("id", id).maybeSingle<Marksheet>();
  if (!ms?.file_path) return;
  const student = await getStudent(ms.student_id);
  const bytes = await readFile("marksheets", ms.file_path);
  if (!student || !bytes) return;
  const r = await checkMarksheet({
    data: bytes,
    mimeType: guessMime(ms.file_name ?? ms.file_path),
    typedName: student.name,
    typedPercentage: ms.typed_percentage === null ? null : Number(ms.typed_percentage),
  });
  await db
    .from("marksheets")
    .update({ ai_check_result: r.result, ai_read_name: r.readName, ai_read_percentage: r.readPercentage, ai_note: r.note })
    .eq("id", id);
  revalidatePath(`/students/${student.id}`);
}

/** Faculty (own batches), Management and Admin can add a note about a student. */
export async function addFacultyNote(form: FormData) {
  const viewer = await requireStaff();
  if (!["faculty", "management", "admin"].includes(viewer.user.role)) return;
  const student = await getStudent(String(form.get("student_id") ?? ""));
  const note = String(form.get("note") ?? "").trim().slice(0, 1000);
  if (!student || !note || !canSeeStudent(viewer, student)) return;
  await adminClient().from("faculty_notes").insert({ student_id: student.id, author_id: viewer.user.id, note });
  revalidatePath(`/students/${student.id}`);
}

/** Mark a student as left (the roll number is never given to anyone else). */
export async function markLeft(form: FormData) {
  const viewer = await requirePermission("students.edit");
  const student = await getStudent(String(form.get("student_id") ?? ""));
  if (!student || student.status !== "active") return;
  await adminClient().from("students").update({ status: "left", updated_at: new Date().toISOString() }).eq("id", student.id);
  await logActivity(viewer, "student.left", { type: "student", id: student.id }, { code: student.code, name: student.name });
  revalidatePath(`/students/${student.id}`);
  redirect(`/students/${student.id}`);
}

/** Bring back a student marked as left. */
export async function markActive(form: FormData) {
  const viewer = await requirePermission("students.edit");
  const student = await getStudent(String(form.get("student_id") ?? ""));
  if (!student || student.status !== "left") return;
  await adminClient().from("students").update({ status: "active", updated_at: new Date().toISOString() }).eq("id", student.id);
  await logActivity(viewer, "student.edit", { type: "student", id: student.id }, { code: student.code, restored: true });
  revalidatePath(`/students/${student.id}`);
  redirect(`/students/${student.id}`);
}
