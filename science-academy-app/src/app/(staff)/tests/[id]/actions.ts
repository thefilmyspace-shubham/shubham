"use server";

import { revalidatePath } from "next/cache";
import { can, canSeeBatch, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { notify, parentUserOf, type NewNotification } from "@/lib/notify";
import { getTest, marksOf, studentsForTest } from "@/lib/academics";
import { visibleBatchIds } from "@/lib/auth";

export type MarksState = { ok: boolean; message: string } | null;

/**
 * Saves the marks of one test. Faculty may enter marks only for students of
 * their own batches; Management and Admin for everyone. A blank score with
 * Absent unticked removes a mark. Parents get "Result added" once per test.
 */
export async function saveMarks(_prev: MarksState, form: FormData): Promise<MarksState> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "marks.enter")) return { ok: false, message: "Your login cannot enter marks." };
  const test = await getTest(String(form.get("testId") ?? ""));
  if (!test) return { ok: false, message: "Test not found." };
  if (test.batch_id && !canSeeBatch(viewer, test.batch_id)) return { ok: false, message: "This test is not for your batch." };
  const max = test.max_marks === null ? null : Number(test.max_marks);

  const students = await studentsForTest(test, visibleBatchIds(viewer));
  const existing = new Map((await marksOf([test.id])).map((m) => [m.student_id, m]));

  const upserts: { test_id: string; student_id: string; score: number | null; absent: boolean; entered_by: string; entered_at: string }[] = [];
  const removes: string[] = [];
  const errors: string[] = [];
  const now = new Date().toISOString();
  for (const s of students) {
    const raw = String(form.get(`score-${s.id}`) ?? "").trim();
    const absent = form.get(`absent-${s.id}`) === "on";
    const old = existing.get(s.id);
    if (absent) {
      if (!old?.absent) upserts.push({ test_id: test.id, student_id: s.id, score: null, absent: true, entered_by: viewer.user.id, entered_at: now });
      continue;
    }
    if (!raw) {
      if (old) removes.push(s.id);
      continue;
    }
    const score = Number(raw);
    if (!Number.isFinite(score) || score < 0 || (max !== null && score > max)) {
      errors.push(`${s.name}: ${raw}${max !== null ? ` (max ${max})` : ""}`);
      continue;
    }
    if (old && !old.absent && old.score === score) continue;
    upserts.push({ test_id: test.id, student_id: s.id, score, absent: false, entered_by: viewer.user.id, entered_at: now });
  }
  if (errors.length) return { ok: false, message: `Check these marks: ${errors.slice(0, 5).join(", ")}${errors.length > 5 ? "…" : ""}. Nothing was saved.` };

  const db = adminClient();
  if (upserts.length) {
    const { error } = await db.from("marks").upsert(upserts, { onConflict: "test_id,student_id" });
    if (error) return { ok: false, message: "Could not save marks. Please try again." };
  }
  if (removes.length) await db.from("marks").delete().eq("test_id", test.id).in("student_id", removes);

  if (upserts.length || removes.length) {
    await logActivity(viewer, "marks.save", { type: "test", id: test.id }, { test: test.name, saved: upserts.length, removed: removes.length });
  }

  // Private "Result added" to each parent, once per test and student.
  const byId = new Map(students.map((s) => [s.id, s]));
  const items: NewNotification[] = [];
  for (const u of upserts) {
    const s = byId.get(u.student_id);
    const parent = s ? await parentUserOf(s.id) : null;
    if (!s || !parent) continue;
    items.push({
      userId: parent.id,
      kind: "result",
      title: `Result added: ${test.name}`,
      body: u.absent ? `${s.name}: absent` : `${s.name}: ${u.score}${max !== null ? ` / ${max}` : ""}`,
      link: "/parent/marks",
      dedupeKey: `result-${test.id}-${s.id}`,
    });
  }
  await notify(items);

  revalidatePath(`/tests/${test.id}`);
  revalidatePath("/ranks");
  const changed = upserts.length + removes.length;
  return { ok: true, message: changed ? `Marks saved (${changed} changed).` : "Nothing changed." };
}
