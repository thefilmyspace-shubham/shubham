"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { can, canSeeBatch, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { notify, parentUserOf } from "@/lib/notify";
import { todayIst } from "@/lib/format";
import { canChangeRow, isIsoDate } from "@/lib/attendance";
import type { AttendanceRow, AttendanceStatus, Student } from "@/lib/types";

export type SaveState = { ok: boolean; message: string } | null;

const Entries = z.record(z.string().uuid(), z.enum(["P", "A", "L"]));

/**
 * Saves a batch's attendance for one day. New and recent rows need "Mark
 * attendance"; rows saved more than 24 hours ago are locked and need
 * "Correct attendance" (each correction is logged with old → new).
 */
export async function saveAttendance(_prev: SaveState, form: FormData): Promise<SaveState> {
  const viewer = await staffForApi();
  if (!viewer) return { ok: false, message: "Please log in again." };
  const batchId = String(form.get("batchId") ?? "");
  const date = String(form.get("date") ?? "");
  const note = String(form.get("note") ?? "").trim().slice(0, 1000);
  if (!isIsoDate(date) || date > todayIst()) return { ok: false, message: "Pick a valid date (not in the future)." };
  if (!canSeeBatch(viewer, batchId)) return { ok: false, message: "This batch is not yours." };
  const canMark = can(viewer, "attendance.mark");
  const canCorrect = can(viewer, "attendance.correct");
  if (!canMark && !canCorrect) return { ok: false, message: "Your login cannot mark attendance." };

  let entries: Record<string, AttendanceStatus>;
  try {
    entries = Entries.parse(JSON.parse(String(form.get("entries") ?? "{}")));
  } catch {
    return { ok: false, message: "Could not read the attendance. Please try again." };
  }

  const db = adminClient();
  const { data: studentData } = await db.from("students").select("id, name, code").eq("batch_id", batchId).eq("status", "active");
  const students = (studentData ?? []) as Pick<Student, "id" | "name" | "code">[];
  const inBatch = new Map(students.map((s) => [s.id, s]));
  const ids = Object.keys(entries).filter((id) => inBatch.has(id));
  const { data: existingData } = ids.length
    ? await db.from("attendance").select("*").in("student_id", ids).eq("date", date)
    : { data: [] };
  const existing = new Map(((existingData ?? []) as AttendanceRow[]).map((r) => [r.student_id, r]));

  const now = new Date();
  const inserts: Record<string, unknown>[] = [];
  const updates: { id: string; status: AttendanceStatus }[] = [];
  const corrections: { student: string; code: string | null; from: AttendanceStatus; to: AttendanceStatus }[] = [];
  let refused = 0;
  for (const id of ids) {
    const status = entries[id];
    const row = existing.get(id) ?? null;
    if (row && row.status === status) continue;
    if (!canChangeRow(row, canMark, canCorrect, now)) {
      refused++;
      continue;
    }
    if (!row) {
      inserts.push({ student_id: id, batch_id: batchId, date, status, marked_by: viewer.user.id });
    } else {
      updates.push({ id: row.id, status });
      if (Date.parse(row.locked_at) <= now.getTime()) {
        const s = inBatch.get(id)!;
        corrections.push({ student: s.name, code: s.code, from: row.status, to: status });
      }
    }
  }

  if (inserts.length) {
    const { error } = await db.from("attendance").insert(inserts);
    if (error) return { ok: false, message: "Could not save. Someone may have saved this day just now; please reload." };
  }
  for (const u of updates) {
    // Locked rows stay locked; marked_by keeps who first marked the day.
    await db.from("attendance").update({ status: u.status }).eq("id", u.id);
  }

  if (canMark || canCorrect) {
    if (note) {
      await db.from("attendance_notes").upsert({ batch_id: batchId, date, note, written_by: viewer.user.id });
    } else if (form.has("note")) {
      await db.from("attendance_notes").delete().eq("batch_id", batchId).eq("date", date);
    }
  }

  const fresh = inserts.length + updates.length - corrections.length;
  if (fresh > 0) {
    const count = (s: AttendanceStatus) => ids.filter((id) => entries[id] === s).length;
    await logActivity(viewer, "attendance.save", { type: "batch", id: batchId }, { date, present: count("P"), absent: count("A"), late: count("L"), changed: fresh });
  }
  if (corrections.length) {
    await logActivity(viewer, "attendance.correct", { type: "batch", id: batchId }, { date, changes: corrections });
  }

  revalidatePath("/attendance");
  revalidatePath(`/attendance/${batchId}`);
  const saved = inserts.length + updates.length;
  if (refused) {
    return { ok: saved > 0, message: `${saved} saved. ${refused} locked ${refused === 1 ? "row was" : "rows were"} not changed (locked 24 hours after saving; only Admin or Management can correct).` };
  }
  return { ok: true, message: saved ? `Attendance saved (${saved} ${saved === 1 ? "student" : "students"}).` : note ? "Note saved." : "Nothing changed." };
}

/** Sends the ready attendance message privately to the student's parent login. */
export async function sendAttendanceAlert(_prev: SaveState, form: FormData): Promise<SaveState> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "students.view")) return { ok: false, message: "Not allowed." };
  const studentId = String(form.get("studentId") ?? "");
  const message = String(form.get("message") ?? "").trim().slice(0, 600);
  if (!message) return { ok: false, message: "The message is empty." };
  const { data: s } = await adminClient().from("students").select("id, batch_id, name").eq("id", studentId).maybeSingle<Pick<Student, "id" | "batch_id" | "name">>();
  if (!s || !canSeeBatch(viewer, s.batch_id)) return { ok: false, message: "Student not found." };
  const parent = await parentUserOf(s.id);
  if (!parent) return { ok: false, message: "This student has no login number yet." };
  await notify([
    {
      userId: parent.id,
      kind: "attendance",
      title: `Attendance: ${s.name}`,
      body: message,
      link: "/parent/notifications",
      dedupeKey: `attendance-alert-${s.id}-${todayIst()}`,
    },
  ]);
  await logActivity(viewer, "attendance.alert", { type: "student", id: s.id }, {});
  return { ok: true, message: "Sent to the parent's app." };
}
