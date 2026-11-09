// Attendance (spec §11). Pure rules first (unit tested), then data loaders.

import "server-only";
import { adminClient } from "./supabase/admin";
import { addDays } from "./format";
import type { AttendanceRow, AttendanceStatus } from "./types";

export const LOW_ATTENDANCE_PCT = 75;
export const ABSENT_STREAK_FLAG = 3;
export const LOCK_HOURS = 24;

/** Locked 24 hours after saving. */
export function isLocked(lockedAt: string, now: Date = new Date()): boolean {
  return Date.parse(lockedAt) <= now.getTime();
}

/**
 * Who may change one row:
 *  - not saved yet, or saved less than 24 hours ago: whoever may mark attendance
 *  - locked: only who may correct attendance (Admin; Management, logged)
 */
export function canChangeRow(row: Pick<AttendanceRow, "locked_at"> | null, canMark: boolean, canCorrect: boolean, now: Date = new Date()): boolean {
  if (!row) return canMark;
  return isLocked(row.locked_at, now) ? canCorrect : canMark || canCorrect;
}

/** Late counts as present. */
export function attendancePct(statuses: AttendanceStatus[]): number | null {
  if (!statuses.length) return null;
  const present = statuses.filter((s) => s !== "A").length;
  return Math.round((present / statuses.length) * 100);
}

/** Absences in a row up to the latest marked day. Input: rows in any order. */
export function trailingAbsences(rows: { date: string; status: AttendanceStatus }[]): { count: number; dates: string[] } {
  const sorted = [...rows].sort((a, b) => b.date.localeCompare(a.date));
  const dates: string[] = [];
  for (const r of sorted) {
    if (r.status !== "A") break;
    dates.push(r.date);
  }
  return { count: dates.length, dates: dates.reverse() };
}

export function countStatuses(statuses: (AttendanceStatus | undefined | null)[]): { P: number; A: number; L: number; unmarked: number } {
  const c = { P: 0, A: 0, L: 0, unmarked: 0 };
  for (const s of statuses) {
    if (s === "P" || s === "A" || s === "L") c[s]++;
    else c.unmarked++;
  }
  return c;
}

export const STATUS_LABEL: Record<AttendanceStatus, string> = { P: "Present", A: "Absent", L: "Late" };

export function isIsoDate(s: string | null | undefined): s is string {
  return Boolean(s && /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(`${s}T00:00:00Z`)));
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

export async function attendanceOn(studentIds: string[], date: string): Promise<AttendanceRow[]> {
  if (!studentIds.length) return [];
  const { data } = await adminClient().from("attendance").select("*").in("student_id", studentIds).eq("date", date);
  return (data ?? []) as AttendanceRow[];
}

export async function attendanceBetween(studentIds: string[], from: string, to: string): Promise<AttendanceRow[]> {
  if (!studentIds.length) return [];
  const rows: AttendanceRow[] = [];
  // Page through (Supabase returns at most 1000 rows per call).
  for (let start = 0; ; start += 1000) {
    const { data } = await adminClient()
      .from("attendance")
      .select("*")
      .in("student_id", studentIds)
      .gte("date", from)
      .lte("date", to)
      .order("date")
      .range(start, start + 999);
    const page = (data ?? []) as AttendanceRow[];
    rows.push(...page);
    if (page.length < 1000) break;
  }
  return rows;
}

export type AttendanceFlag = {
  studentId: string;
  pct: number | null;
  days: number;
  streak: number;
  streakDates: string[];
  low: boolean;
};

/** Low attendance (below 75% over the last 30 days) and absent-in-a-row flags. */
export function flagsFor(rows: AttendanceRow[]): Map<string, AttendanceFlag> {
  const byStudent = new Map<string, AttendanceRow[]>();
  for (const r of rows) {
    const list = byStudent.get(r.student_id) ?? [];
    list.push(r);
    byStudent.set(r.student_id, list);
  }
  const out = new Map<string, AttendanceFlag>();
  for (const [studentId, list] of byStudent) {
    const pct = attendancePct(list.map((r) => r.status));
    const streak = trailingAbsences(list);
    out.set(studentId, {
      studentId,
      pct,
      days: list.length,
      streak: streak.count,
      streakDates: streak.dates,
      low: pct !== null && pct < LOW_ATTENDANCE_PCT,
    });
  }
  return out;
}

export function windowStart(today: string, days = 30): string {
  return addDays(today, -(days - 1));
}
