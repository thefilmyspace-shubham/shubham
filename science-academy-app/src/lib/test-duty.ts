import "server-only";
import { can, canSeeBatch, visibleBatchIds, type Viewer } from "./auth";
import { adminClient } from "./supabase/admin";
import type { Test } from "./types";

export type TestAccess = {
  /** May open the test's attendance and marks pages at all. */
  see: boolean;
  /** Batches whose students this person handles (null = every student of the test). */
  scope: string[] | null;
  /** The faculty member on duty for this test. */
  onDuty: boolean;
  /** May mark attendance and press "Test done". */
  canRun: boolean;
};

/**
 * Who handles a test: Admin/Management (academics.edit) and the faculty on
 * duty handle every student of it; other faculty only their own batches.
 */
export function testAccess(viewer: Viewer, test: Test): TestAccess {
  const onDuty = Boolean(test.faculty_id) && test.faculty_id === viewer.user.id;
  const editor = can(viewer, "academics.edit");
  if (onDuty || editor) return { see: true, scope: null, onDuty, canRun: true };
  const scope = visibleBatchIds(viewer);
  const see = test.batch_id ? canSeeBatch(viewer, test.batch_id) : true;
  return { see, scope, onDuty, canRun: see && can(viewer, "attendance.mark") };
}

/** Tests a faculty member is on duty for, from a date on. */
export async function dutyTests(userId: string, fromDate: string): Promise<Test[]> {
  const { data } = await adminClient().from("tests").select("*").eq("faculty_id", userId).gte("date", fromDate).order("date").order("start_time").limit(100);
  return (data ?? []) as Test[];
}

export type TestMark = { status: "P" | "A" | "L"; markedAt: string };

/** Hours after which faculty can no longer change a test's attendance (Admin/Management still can). */
export const TEST_ATT_LOCK_HOURS = 2;

export function testMarkLocked(markedAt: string, now = Date.now()): boolean {
  return now - new Date(markedAt).getTime() > TEST_ATT_LOCK_HOURS * 3600_000;
}

/** Each student's test attendance. Works before the "late" column exists too. */
export async function testAttendanceOf(testId: string): Promise<Map<string, TestMark>> {
  const db = adminClient();
  const full = await db.from("test_attendance").select("student_id, present, late, marked_at").eq("test_id", testId);
  const data: unknown[] | null = full.error ? (await db.from("test_attendance").select("student_id, present, marked_at").eq("test_id", testId)).data : full.data;
  return new Map(
    ((data ?? []) as { student_id: string; present: boolean; late?: boolean; marked_at: string }[]).map((r) => [
      r.student_id,
      { status: !r.present ? "A" : r.late ? "L" : "P", markedAt: r.marked_at },
    ]),
  );
}

/** How many students of each test have their attendance marked. */
export async function testAttendanceCounts(testIds: string[]): Promise<Map<string, { present: number; absent: number }>> {
  const out = new Map<string, { present: number; absent: number }>();
  if (!testIds.length) return out;
  const { data } = await adminClient().from("test_attendance").select("test_id, present").in("test_id", testIds);
  for (const r of (data ?? []) as { test_id: string; present: boolean }[]) {
    const c = out.get(r.test_id) ?? { present: 0, absent: 0 };
    if (r.present) c.present++;
    else c.absent++;
    out.set(r.test_id, c);
  }
  return out;
}
