"use server";

import { revalidatePath } from "next/cache";
import { staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { getTest, studentsForTest } from "@/lib/academics";
import { testAccess } from "@/lib/test-duty";
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
  const now = new Date().toISOString();
  const rows = students
    .filter((s) => entries[s.id] === "P" || entries[s.id] === "A")
    .map((s) => ({ test_id: test.id, student_id: s.id, present: entries[s.id] === "P", marked_by: viewer.user.id, marked_at: now }));
  const db = adminClient();
  if (rows.length) {
    const { error } = await db.from("test_attendance").upsert(rows, { onConflict: "test_id,student_id" });
    if (error) return { ok: false, message: t("academics.duty.couldNotSave") };
  }
  const markDone = form.get("done") === "1";
  if (markDone && !test.done_at) await db.from("tests").update({ done_at: now, done_by: viewer.user.id }).eq("id", test.id);
  await logActivity(viewer, "test.save", { type: "test", id: test.id }, {
    name: test.name,
    attendance: { present: rows.filter((r) => r.present).length, absent: rows.filter((r) => !r.present).length },
    done: markDone || undefined,
  });
  revalidatePath(`/tests/${test.id}`, "layout");
  revalidatePath("/timetable");
  revalidatePath("/");
  const absent = rows.filter((r) => !r.present).length;
  return {
    ok: true,
    done: markDone,
    message: markDone
      ? t("academics.duty.savedDone", { present: rows.length - absent, absent })
      : t("academics.duty.saved", { present: rows.length - absent, absent }),
  };
}
