import "server-only";
import { z } from "zod";
import { adminClient } from "./supabase/admin";
import { formatStudentId, normalizeMobile, parseStudentId, type Board } from "./ids";
import { addMonths, monthStart, todayIst } from "./format";
import type { AttendanceStatus, Guardian, GuardianRelation, Marksheet, Student } from "./types";

export const RELATIONS: GuardianRelation[] = ["father", "mother", "guardian", "alternate"];
export const RELATION_LABEL: Record<GuardianRelation, string> = {
  father: "Father",
  mother: "Mother",
  guardian: "Guardian",
  alternate: "Alternate",
};

export const CONSENT_VERSION = "v1";
export const CONSENT_TEXT =
  "I, the parent or guardian, agree that Science Academy may store my child's details, my contact numbers and the uploaded marksheets, and use them only to run my child's coaching (attendance, fees, tests and messages to me).";

export type IdHistoryRow = {
  id: string;
  student_id: string;
  roll_number: number;
  board: Board;
  class: number;
  session_year: number;
  code: string;
  valid_from: string;
  valid_to: string | null;
};

// ---------------------------------------------------------------------------
// Registration form (pure parts are unit tested)
// ---------------------------------------------------------------------------

const optionalText = z
  .string()
  .trim()
  .max(120)
  .transform((s) => (s ? s : null));

export const RegistrationSchema = z.object({
  name: z.string().trim().min(2, "Enter the student's name.").max(120),
  board: z.enum(["CB", "MP"], { message: "Choose the board." }),
  current_class: z.coerce.number().int().min(6, "Choose the class.").max(12, "Choose the class."),
  session_year: z.coerce.number().int().min(0).max(99),
  school: optionalText,
  batch_id: z
    .string()
    .trim()
    .transform((s) => (s ? s : null)),
  father_name: optionalText,
  mother_name: optionalText,
  guardian_name: optionalText,
  email: z
    .string()
    .trim()
    .max(160)
    .transform((s) => (s ? s.toLowerCase() : null))
    .refine((s) => s === null || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s), "Email does not look right."),
  monthly_fee: z.coerce.number().min(0, "Fee cannot be negative.").max(1_00_000, "Fee looks too high."),
});

export type RegistrationInput = z.infer<typeof RegistrationSchema>;

export type GuardianInput = { relation: GuardianRelation; name: string | null; mobile: string };

export type ParsedRegistration = {
  student: RegistrationInput;
  guardians: GuardianInput[];
  loginRelation: GuardianRelation | null;
  consent: boolean;
  consentBy: string | null;
};

export type FieldErrors = Record<string, string>;

/**
 * Reads the registration form. For "register" the rules are strict (batch,
 * login number, consent); a draft only needs the name, board and class.
 */
export function parseRegistration(
  form: FormData,
  intent: "draft" | "register",
): { ok: true; data: ParsedRegistration } | { ok: false; errors: FieldErrors } {
  const get = (k: string) => String(form.get(k) ?? "");
  const errors: FieldErrors = {};
  const parsed = RegistrationSchema.safeParse({
    name: get("name"),
    board: get("board"),
    current_class: get("current_class") || "0",
    session_year: get("session_year"),
    school: get("school"),
    batch_id: get("batch_id"),
    father_name: get("father_name"),
    mother_name: get("mother_name"),
    guardian_name: get("guardian_name"),
    email: get("email"),
    monthly_fee: get("monthly_fee") || "0",
  });
  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      const key = String(issue.path[0] ?? "form");
      errors[key] ??= issue.message;
    }
  }

  const names: Record<GuardianRelation, string | null> = {
    father: get("father_name").trim() || null,
    mother: get("mother_name").trim() || null,
    guardian: get("guardian_name").trim() || null,
    alternate: get("alternate_name").trim() || null,
  };
  const guardians: GuardianInput[] = [];
  const seen = new Set<string>();
  for (const rel of RELATIONS) {
    const raw = get(`${rel}_mobile`).trim();
    if (!raw) continue;
    const mobile = normalizeMobile(raw);
    if (!mobile) {
      errors[`${rel}_mobile`] = "Enter a 10 digit mobile number.";
      continue;
    }
    if (seen.has(mobile)) {
      errors[`${rel}_mobile`] = "This number is already entered above.";
      continue;
    }
    seen.add(mobile);
    guardians.push({ relation: rel, name: names[rel], mobile });
  }

  const loginRaw = get("login_relation");
  const loginRelation = (RELATIONS as string[]).includes(loginRaw) ? (loginRaw as GuardianRelation) : null;
  const consent = form.get("consent") === "on" || form.get("consent") === "true";
  const consentBy = get("consent_by").trim() || null;

  if (loginRelation && !guardians.some((g) => g.relation === loginRelation)) {
    errors.login_relation = "The login number must be one of the numbers entered.";
  }
  if (intent === "register") {
    if (!get("batch_id").trim()) errors.batch_id ??= "Choose the batch.";
    if (!guardians.length) errors.father_mobile ??= "Enter at least one mobile number.";
    else if (!loginRelation) errors.login_relation ??= "Choose which number is the login number.";
    if (!consent) errors.consent = "The parent or guardian must agree before registering.";
    else if (!consentBy) errors.consent_by = "Who gave the consent?";
  }

  if (Object.keys(errors).length || !parsed.success) return { ok: false, errors };
  return { ok: true, data: { student: parsed.data, guardians, loginRelation, consent, consentBy } };
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export async function getStudent(id: string): Promise<Student | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const { data } = await adminClient().from("students").select("*").eq("id", id).maybeSingle<Student>();
  return data ?? null;
}

export async function studentDetails(id: string) {
  const db = adminClient();
  const [{ data: guardians }, { data: marksheets }, { data: history }, { data: consent }] = await Promise.all([
    db.from("guardians").select("*").eq("student_id", id),
    db.from("marksheets").select("*").eq("student_id", id).order("created_at"),
    db.from("student_id_history").select("*").eq("student_id", id).order("valid_from"),
    db.from("consents").select("*").eq("student_id", id).order("given_at", { ascending: false }).limit(1),
  ]);
  const order = (g: Guardian) => RELATIONS.indexOf(g.relation);
  return {
    guardians: ((guardians ?? []) as Guardian[]).sort((a, b) => order(a) - order(b)),
    marksheets: (marksheets ?? []) as Marksheet[],
    history: (history ?? []) as IdHistoryRow[],
    consent: ((consent ?? []) as { given_by: string; given_at: string; text_version: string }[])[0] ?? null,
  };
}

/** Earlier IDs (not the current one), newest first. */
export function earlierIds(history: IdHistoryRow[], current: string | null): string[] {
  return [...history]
    .filter((h) => h.code !== current)
    .sort((a, b) => b.valid_from.localeCompare(a.valid_from))
    .map((h) => h.code)
    .filter((c, i, all) => all.indexOf(c) === i);
}

/** The next roll number (for the ID preview only; the real one is given on Register). */
export async function nextRollPreview(): Promise<number> {
  const { data } = await adminClient().from("roll_counter").select("last_roll").maybeSingle<{ last_roll: number }>();
  return (data?.last_roll ?? 0) + 1;
}

export type SearchHit = Student & { matchedEarlierId: string | null };

/** "class 9", "9", "MP9", "CB 12" → board/class filter. */
export function parseClassQuery(q: string): { board: Board | null; cls: number } | null {
  const m = /^(?:class\s*)?(cb|mp)?\s*(6|7|8|9|10|11|12)(?:th)?$/i.exec(q.trim());
  if (!m) return null;
  return { board: m[1] ? (m[1].toUpperCase() as Board) : null, cls: Number(m[2]) };
}

/**
 * Finds students by current or earlier ID, name, a parent's mobile number, or
 * class. batchIds limits the result (Faculty: own batches); null = all.
 */
export async function findStudentsByText(
  text: string,
  opts: { batchIds?: string[] | null; limit?: number; includeDrafts?: boolean } = {},
): Promise<SearchHit[]> {
  const q = text.trim();
  if (q.length < 2) return [];
  const db = adminClient();
  const limit = opts.limit ?? 30;
  const statuses = opts.includeDrafts ? ["active", "draft", "left", "passed_out"] : ["active", "left", "passed_out"];
  const ids = new Map<string, string | null>(); // student id → matched earlier id

  const asId = parseStudentId(q);
  const mobile = normalizeMobile(q);
  const cls = parseClassQuery(q);

  if (asId) {
    const code = formatStudentId(asId.board, asId.cls, asId.roll, asId.session);
    const [{ data: cur }, { data: hist }] = await Promise.all([
      db.from("students").select("id").eq("code", code),
      db.from("student_id_history").select("student_id, code").eq("code", code),
    ]);
    for (const r of (cur ?? []) as { id: string }[]) ids.set(r.id, null);
    for (const r of (hist ?? []) as { student_id: string; code: string }[]) if (!ids.has(r.student_id)) ids.set(r.student_id, r.code);
    // Same roll, any ID (the roll never changes).
    if (!ids.size) {
      const { data: byRoll } = await db.from("students").select("id").eq("roll_number", asId.roll);
      for (const r of (byRoll ?? []) as { id: string }[]) ids.set(r.id, code);
    }
  } else if (mobile) {
    const { data } = await db.from("guardians").select("student_id").eq("mobile", mobile);
    for (const r of (data ?? []) as { student_id: string }[]) ids.set(r.student_id, null);
  } else if (/^\d{3,4}$/.test(q)) {
    const { data } = await db.from("students").select("id").eq("roll_number", Number(q));
    for (const r of (data ?? []) as { id: string }[]) ids.set(r.id, null);
  }

  let query = db.from("students").select("*").in("status", statuses);
  if (ids.size) {
    query = query.in("id", [...ids.keys()]);
  } else if (cls) {
    query = query.eq("current_class", cls.cls);
    if (cls.board) query = query.eq("board", cls.board);
  } else if (!asId && !mobile) {
    const safe = q.replace(/[%_,()]/g, " ").trim();
    if (!safe) return [];
    query = query.or(`name.ilike.%${safe}%,code.ilike.%${safe}%`);
  } else {
    return [];
  }
  if (opts.batchIds) {
    if (!opts.batchIds.length) return [];
    query = query.in("batch_id", opts.batchIds);
  }
  const { data } = await query.order("name").limit(limit);
  return ((data ?? []) as Student[]).map((s) => ({ ...s, matchedEarlierId: ids.get(s.id) ?? null }));
}

// ---------------------------------------------------------------------------
// Profile numbers
// ---------------------------------------------------------------------------

export type TestResult = {
  test_id: string;
  name: string;
  date: string;
  tag: "School" | "Coaching";
  subject: string | null;
  score: number | null;
  absent: boolean;
  max_marks: number | null;
  pct: number | null;
};

type MarkJoin = {
  test_id: string;
  student_id: string;
  score: number | null;
  absent: boolean;
  tests: { name: string; date: string; tag: "School" | "Coaching"; subject: string | null; max_marks: number | null } | null;
};

function pctOf(score: number | null, max: number | null): number | null {
  if (score === null || !max || Number(max) <= 0) return null;
  return Math.round((Number(score) / Number(max)) * 1000) / 10;
}

export async function studentProfileNumbers(student: Student, today = todayIst()) {
  const db = adminClient();
  const sixAgo = addMonths(monthStart(today), -5);
  const [{ data: att }, { data: marks }] = await Promise.all([
    db.from("attendance").select("date, status").eq("student_id", student.id).gte("date", sixAgo),
    db
      .from("marks")
      .select("test_id, student_id, score, absent, tests(name, date, tag, subject, max_marks)")
      .eq("student_id", student.id),
  ]);

  const rows = (att ?? []) as { date: string; status: AttendanceStatus }[];
  const months = Array.from({ length: 6 }, (_, i) => addMonths(sixAgo, i));
  const byMonth = months.map((m) => {
    const inMonth = rows.filter((r) => r.date.startsWith(m.slice(0, 7)));
    const present = inMonth.filter((r) => r.status !== "A").length;
    return { month: m, total: inMonth.length, present, pct: inMonth.length ? Math.round((present / inMonth.length) * 100) : 0 };
  });
  const thisMonth = byMonth[byMonth.length - 1];

  const results: TestResult[] = ((marks ?? []) as unknown as MarkJoin[])
    .filter((m) => m.tests)
    .map((m) => ({
      test_id: m.test_id,
      name: m.tests!.name,
      date: m.tests!.date,
      tag: m.tests!.tag,
      subject: m.tests!.subject,
      score: m.score === null ? null : Number(m.score),
      absent: m.absent,
      max_marks: m.tests!.max_marks === null ? null : Number(m.tests!.max_marks),
      pct: m.absent ? null : pctOf(m.score, m.tests!.max_marks),
    }))
    .sort((a, b) => b.date.localeCompare(a.date));
  const pcts = results.map((r) => r.pct).filter((p): p is number => p !== null);
  const average = pcts.length ? Math.round((pcts.reduce((a, b) => a + b, 0) / pcts.length) * 10) / 10 : null;

  const rank = average === null ? null : await classRank(student);
  return { attendance: { thisMonth, byMonth }, results, average, rank };
}

/**
 * Rank in class: position by average test percentage among active students
 * of the same board and class (only students with at least one scored test).
 */
async function classRank(student: Student): Promise<{ rank: number; of: number } | null> {
  const db = adminClient();
  const { data: tests } = await db
    .from("tests")
    .select("id, max_marks")
    .eq("board", student.board)
    .eq("class", student.current_class)
    .not("max_marks", "is", null);
  const testList = (tests ?? []) as { id: string; max_marks: number }[];
  if (!testList.length) return null;
  const maxById = new Map(testList.map((t) => [t.id, Number(t.max_marks)]));
  const [{ data: marks }, { data: classmates }] = await Promise.all([
    db.from("marks").select("student_id, test_id, score, absent").in("test_id", [...maxById.keys()]).eq("absent", false),
    db.from("students").select("id").eq("board", student.board).eq("current_class", student.current_class).eq("status", "active"),
  ]);
  const active = new Set(((classmates ?? []) as { id: string }[]).map((s) => s.id));
  const sums = new Map<string, { total: number; n: number }>();
  for (const m of (marks ?? []) as { student_id: string; test_id: string; score: number | null }[]) {
    if (!active.has(m.student_id) || m.score === null) continue;
    const p = pctOf(m.score, maxById.get(m.test_id) ?? null);
    if (p === null) continue;
    const s = sums.get(m.student_id) ?? { total: 0, n: 0 };
    s.total += p;
    s.n += 1;
    sums.set(m.student_id, s);
  }
  if (!sums.has(student.id)) return null;
  const averages = [...sums.values()].map((s) => s.total / s.n);
  const myAvg = sums.get(student.id)!.total / sums.get(student.id)!.n;
  return { rank: 1 + averages.filter((a) => a > myAvg + 1e-9).length, of: averages.length };
}

export type FacultyNote = { id: string; note: string; created_at: string; author: { staff_id: string | null; name: string } | null };

export async function facultyNotes(studentId: string): Promise<FacultyNote[]> {
  const { data } = await adminClient()
    .from("faculty_notes")
    .select("id, note, created_at, author:users(staff_id, name)")
    .eq("student_id", studentId)
    .order("created_at", { ascending: false })
    .limit(5);
  return (data ?? []) as unknown as FacultyNote[];
}

/** Write the current ID into the history (closing the previous current row). */
export async function recordIdChange(student: Pick<Student, "id" | "roll_number" | "board" | "current_class" | "session_year">, today = todayIst()) {
  if (student.roll_number === null) return;
  const db = adminClient();
  const code = formatStudentId(student.board, student.current_class, student.roll_number, student.session_year);
  const { data: open } = await db.from("student_id_history").select("id, code").eq("student_id", student.id).is("valid_to", null);
  const openRows = (open ?? []) as { id: string; code: string }[];
  if (openRows.length === 1 && openRows[0].code === code) return;
  if (openRows.length) {
    await db
      .from("student_id_history")
      .update({ valid_to: today })
      .in(
        "id",
        openRows.map((r) => r.id),
      );
  }
  await db.from("student_id_history").insert({
    student_id: student.id,
    roll_number: student.roll_number,
    board: student.board,
    class: student.current_class,
    session_year: student.session_year,
    code,
    valid_from: today,
  });
}
