"use server";

import { revalidatePath } from "next/cache";
import { can, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { getTest, studentsForTest } from "@/lib/academics";
import { testAccess, testAttendanceOf, testMarkLocked } from "@/lib/test-duty";
import { getT } from "@/lib/i18n/server";

export type TestAttState = { ok: boolean; message: string; done?: boolean } | null;

/**
 * Who came to a test. The faculty on duty and Admin/Management mark every
 * student of the test; other faculty their own batches. "Save and mark test
 * done" also closes the test (it moves from Upcoming to marks).
 */
export async function saveTestAttendance(_prev: TestAttState, form: FormData): Promise<TestAttState> {
  const { t } = await getT();
  const viewer = await staffForApi();
  if (!viewer) return { ok: false, message: t("academics.duty.noAccess") };
  const test = await getTest(String(form.get("testId") ?? ""));
  if (!test) return { ok: false, message: t("academics.marks.testNotFound") };
  const access = testAccess(viewer, test);
  if (!access.canRun) return { ok: false, message: t("academics.duty.noAccess") };

  let entries: Record<string, unknown> = {};
  try {
    entries = JSON.parse(String(form.get("entries") ?? "{}"));
  } catch {
    return { ok: false, message: t("academics.duty.noAccess") };
  }
  const students = await studentsForTest(test, access.scope);
  const before = await testAttendanceOf(test.id);
  // Faculty can change a mark only for 2 hours; Admin/Management can always correct.
  const canCorrect = can(viewer, "academics.edit");
  const now = new Date().toISOString();
  let lockedSkipped = 0;
  const changed: { student_id: string; status: "P" | "A" | "L" }[] = [];
  for (const s of students) {
    const v = entries[s.id];
    if (v !== "P" && v !== "A" && v !== "L") continue;
    const old = before.get(s.id);
    if (old?.status === v) continue;
    if (old && !canCorrect && testMarkLocked(old.markedAt)) {
      lockedSkipped++;
      continue;
    }
    changed.push({ student_id: s.id, status: v });
  }
  const rows = changed.map((c) => ({ test_id: test.id, student_id: c.student_id, present: c.status !== "A", late: c.status === "L", marked_by: viewer.user.id, marked_at: now }));
  const db = adminClient();
  if (rows.length) {
    let { error } = await db.from("test_attendance").upsert(rows, { onConflict: "test_id,student_id" });
    // "late" column not added yet (SQL test_late): save as present.
    if (error && /late|schema cache|42703|PGRST204/i.test(`${error.code} ${error.message}`)) {
      ({ error } = await db.from("test_attendance").upsert(
        rows.map(({ late: _late, ...r }) => (void _late, r)),
        { onConflict: "test_id,student_id" },
      ));
    }
    if (error) return { ok: false, message: t("academics.duty.couldNotSave") };
  }
  const corrected = changed.filter((c) => before.has(c.student_id)).length;
  const markDone = form.get("done") === "1";
  if (markDone && !test.done_at) await db.from("tests").update({ done_at: now, done_by: viewer.user.id }).eq("id", test.id);
  await logActivity(viewer, "test.save", { type: "test", id: test.id }, {
    name: test.name,
    attendance: { present: rows.filter((r) => r.present && !r.late).length, late: rows.filter((r) => r.late).length, absent: rows.filter((r) => !r.present).length },
    corrected: corrected || undefined,
    done: markDone || undefined,
  });
  revalidatePath(`/tests/${test.id}`, "layout");
  revalidatePath("/timetable");
  revalidatePath("/");
  // Totals over the whole sheet, not only what changed now.
  const after = await testAttendanceOf(test.id);
  const mine = students.map((s) => after.get(s.id)?.status).filter(Boolean);
  const counts = { present: mine.filter((x) => x === "P").length, late: mine.filter((x) => x === "L").length, absent: mine.filter((x) => x === "A").length };
  const message = markDone ? t("academics.duty.savedDone", counts) : t("academics.duty.saved", counts);
  return {
    ok: true,
    done: markDone,
    message: lockedSkipped ? `${message} ${t("academics.duty.lockedSkipped", { n: lockedSkipped })}` : message,
  };
}
