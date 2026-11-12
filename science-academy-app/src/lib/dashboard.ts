import "server-only";
import { adminClient } from "./supabase/admin";
import { addDays, addMonths, monthStart, todayIst } from "./format";
import { balanceOf, daysLate, dueDate } from "./fees";
import type { Batch, CallLogRow, Student, Test, TimetableEntry } from "./types";

// Numbers for the Home dashboards (spec §7) and the daily reminders.
// Callers check permissions first (fees only with fees.view).

type Builder<T> = { range: (from: number, to: number) => PromiseLike<{ data: T[] | null }> };

/** Reads every row (PostgREST returns at most 1000 per request). */
export async function fetchAll<T>(make: () => Builder<T>, page = 1000): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += page) {
    const { data } = await make().range(from, from + page - 1);
    const rows = data ?? [];
    out.push(...rows);
    if (rows.length < page) return out;
  }
}

export type StudentLite = Pick<Student, "id" | "name" | "board" | "current_class" | "batch_id" | "code">;

export async function activeStudents(batchIds: string[] | null = null): Promise<StudentLite[]> {
  if (batchIds && !batchIds.length) return [];
  return fetchAll<StudentLite>(() => {
    let q = adminClient().from("students").select("id, name, board, current_class, batch_id, code").eq("status", "active");
    if (batchIds) q = q.in("batch_id", batchIds);
    return q.order("id");
  });
}

// ---------------------------------------------------------------- fees

export type Owing = { studentId: string; balance: number; overdue: number; oldestMonth: string; daysLate: number };

export type FeeOverview = {
  pendingTotal: number;
  overdueTotal: number;
  owing: Map<string, Owing>;
  byClass: { board: string; cls: number; amount: number; students: number }[];
};

/** Money still owed for this month and earlier, by active students. */
export async function feeOverview(today: string, students: StudentLite[]): Promise<FeeOverview> {
  const current = monthStart(today);
  const rows = await fetchAll<{ student_id: string; month: string; amount: number; paid: number; due_date?: string | null }>(() =>
    adminClient().from("fees_ledger").select("*").lte("month", current).order("id"),
  );
  const byId = new Map(students.map((s) => [s.id, s]));
  const owing = new Map<string, Owing>();
  for (const r of rows) {
    const bal = balanceOf(r);
    if (bal <= 0 || !byId.has(r.student_id)) continue;
    const late = today > (r.due_date ? String(r.due_date).slice(0, 10) : dueDate(r.month));
    const o = owing.get(r.student_id) ?? { studentId: r.student_id, balance: 0, overdue: 0, oldestMonth: r.month, daysLate: 0 };
    o.balance += bal;
    if (late) o.overdue += bal;
    if (r.month < o.oldestMonth) o.oldestMonth = r.month;
    o.daysLate = Math.max(o.daysLate, late ? daysLate(r.month, today, r.due_date) : 0);
    owing.set(r.student_id, o);
  }
  const classes = new Map<string, { board: string; cls: number; amount: number; students: number }>();
  let pendingTotal = 0;
  let overdueTotal = 0;
  for (const o of owing.values()) {
    pendingTotal += o.balance;
    overdueTotal += o.overdue;
    const s = byId.get(o.studentId)!;
    const key = `${s.board}${s.current_class}`;
    const c = classes.get(key) ?? { board: s.board, cls: s.current_class, amount: 0, students: 0 };
    c.amount += o.balance;
    c.students += 1;
    classes.set(key, c);
  }
  const byClass = [...classes.values()].sort((a, b) => a.board.localeCompare(b.board) || a.cls - b.cls);
  return { pendingTotal, overdueTotal, owing, byClass };
}

/** Money received (bills not cancelled) from `from` to `to` inclusive. */
export async function collected(from: string, to: string): Promise<number> {
  const rows = await fetchAll<{ received: number }>(() =>
    adminClient().from("invoices").select("received").eq("status", "issued").gte("paid_on", from).lte("paid_on", to).order("id"),
  );
  return rows.reduce((sum, r) => sum + Number(r.received), 0);
}

/** Collection per month for the last n months (oldest first). */
export async function collectionByMonth(today: string, n = 6): Promise<{ month: string; amount: number }[]> {
  const current = monthStart(today);
  const first = addMonths(current, -(n - 1));
  const rows = await fetchAll<{ received: number; paid_on: string }>(() =>
    adminClient().from("invoices").select("received, paid_on").eq("status", "issued").gte("paid_on", first).lte("paid_on", addDays(addMonths(current, 1), -1)).order("id"),
  );
  const months = Array.from({ length: n }, (_, i) => addMonths(first, i));
  const sums = new Map(months.map((m) => [m, 0]));
  for (const r of rows) {
    const m = monthStart(r.paid_on);
    sums.set(m, (sums.get(m) ?? 0) + Number(r.received));
  }
  return months.map((m) => ({ month: m, amount: sums.get(m) ?? 0 }));
}

/** Fee reminder chain for a month: reminded → called → escalated (distinct students). */
export async function reminderChain(month: string): Promise<{ reminded: number; called: number; escalated: number }> {
  const rows = await fetchAll<{ student_id: string; stage: string }>(() =>
    adminClient().from("fee_reminders").select("student_id, stage").eq("month", month).order("id"),
  );
  const sets = { reminded: new Set<string>(), called: new Set<string>(), escalated: new Set<string>() };
  for (const r of rows) {
    if (r.stage in sets) sets[r.stage as keyof typeof sets].add(r.student_id);
  }
  return { reminded: sets.reminded.size, called: sets.called.size, escalated: sets.escalated.size };
}

/** Latest call per student (most recent first). */
export async function latestCalls(sinceDays = 120): Promise<Map<string, CallLogRow>> {
  const since = new Date(Date.now() - sinceDays * 86_400_000).toISOString();
  const rows = await fetchAll<CallLogRow>(() =>
    adminClient().from("call_log").select("*").gte("created_at", since).order("created_at", { ascending: false }),
  );
  const out = new Map<string, CallLogRow>();
  for (const r of rows) if (!out.has(r.student_id)) out.set(r.student_id, r);
  return out;
}

export type CallDue = { studentId: string; reason: "overdue" | "promised_today" | "promise_broken"; owing: Owing; lastCall: CallLogRow | null };

/**
 * Parents to call: money overdue, unless they promised a date that has not
 * come yet. A promise due today (or broken) is on the list too.
 */
export function callsDue(fees: FeeOverview, calls: Map<string, CallLogRow>, today: string): CallDue[] {
  const out: CallDue[] = [];
  for (const o of fees.owing.values()) {
    if (o.overdue <= 0) continue;
    const last = calls.get(o.studentId) ?? null;
    // Already called today: not due again until tomorrow.
    if (last && todayIst(new Date(last.created_at)) === today) continue;
    if (last?.outcome === "promised_date" && last.follow_up_date) {
      if (last.follow_up_date > today) continue;
      out.push({ studentId: o.studentId, reason: last.follow_up_date === today ? "promised_today" : "promise_broken", owing: o, lastCall: last });
      continue;
    }
    if (last?.outcome === "will_pay_today" && last.created_at.slice(0, 10) >= addDays(today, -1)) continue;
    out.push({ studentId: o.studentId, reason: "overdue", owing: o, lastCall: last });
  }
  return out.sort((a, b) => b.owing.daysLate - a.owing.daysLate);
}

/** Students whose latest call said "Needs admin" and who still owe money. */
export function escalations(fees: FeeOverview, calls: Map<string, CallLogRow>): CallLogRow[] {
  return [...calls.values()].filter((c) => c.outcome === "needs_admin" && (fees.owing.get(c.student_id)?.balance ?? 0) > 0);
}

// ---------------------------------------------------------------- attendance

export type DayAttendance = { present: number; late: number; absent: number; total: number; pct: number; markedBatches: Set<string> };

export async function attendanceOn(date: string, batchIds: string[] | null = null): Promise<DayAttendance> {
  if (batchIds && !batchIds.length) return { present: 0, late: 0, absent: 0, total: 0, pct: 0, markedBatches: new Set() };
  const rows = await fetchAll<{ batch_id: string; status: string }>(() => {
    let q = adminClient().from("attendance").select("batch_id, status").eq("date", date);
    if (batchIds) q = q.in("batch_id", batchIds);
    return q.order("id");
  });
  const r = { present: 0, late: 0, absent: 0, total: rows.length, pct: 0, markedBatches: new Set<string>() };
  for (const a of rows) {
    r.markedBatches.add(a.batch_id);
    if (a.status === "P") r.present++;
    else if (a.status === "L") r.late++;
    else r.absent++;
  }
  r.pct = r.total ? Math.round(((r.present + r.late) / r.total) * 100) : 0;
  return r;
}

export async function timetableFor(batchIds: string[] | null): Promise<TimetableEntry[]> {
  if (batchIds && !batchIds.length) return [];
  let q = adminClient().from("timetable_entries").select("*");
  if (batchIds) q = q.in("batch_id", batchIds);
  const { data } = await q.order("start_time");
  return (data ?? []) as TimetableEntry[];
}

/**
 * Does a batch meet on this weekday (1 = Monday)? Its timetable says so;
 * a batch with no timetable yet is taken to meet Monday to Saturday.
 */
export function batchMeets(batchId: string, weekday: number, entries: TimetableEntry[]): boolean {
  const mine = entries.filter((e) => e.batch_id === batchId);
  if (!mine.length) return weekday <= 6;
  return mine.some((e) => e.weekday === weekday);
}

export type LowAttendance = { student: StudentLite; pct: number; marked: number; absentStreak: number };

/**
 * Below 75% over the last 30 days (at least 4 marked days), and anyone absent
 * 3 marked days in a row up to today.
 */
export async function lowAttendance(today: string, students: StudentLite[]): Promise<LowAttendance[]> {
  if (!students.length) return [];
  const from = addDays(today, -30);
  const ids = new Set(students.map((s) => s.id));
  const batchIds = [...new Set(students.map((s) => s.batch_id).filter((b): b is string => Boolean(b)))];
  if (!batchIds.length) return [];
  const rows = await fetchAll<{ student_id: string; date: string; status: string }>(() =>
    adminClient().from("attendance").select("student_id, date, status").in("batch_id", batchIds).gte("date", from).lte("date", today).order("date", { ascending: false }).order("id"),
  );
  const per = new Map<string, { marked: number; present: number; streak: number; streakOpen: boolean }>();
  for (const r of rows) {
    if (!ids.has(r.student_id)) continue;
    const p = per.get(r.student_id) ?? { marked: 0, present: 0, streak: 0, streakOpen: true };
    p.marked++;
    if (r.status !== "A") p.present++;
    if (p.streakOpen) {
      if (r.status === "A") p.streak++;
      else p.streakOpen = false;
    }
    per.set(r.student_id, p);
  }
  const byId = new Map(students.map((s) => [s.id, s]));
  const out: LowAttendance[] = [];
  for (const [id, p] of per) {
    const pct = Math.round((p.present / p.marked) * 100);
    if ((p.marked >= 4 && pct < 75) || p.streak >= 3) out.push({ student: byId.get(id)!, pct, marked: p.marked, absentStreak: p.streak });
  }
  return out.sort((a, b) => b.absentStreak - a.absentStreak || a.pct - b.pct);
}

// ---------------------------------------------------------------- tests

/** Tests from today on, for these batches (and whole-class tests of their classes). */
export async function upcomingTests(today: string, days: number, batches: Batch[] | null): Promise<Test[]> {
  const { data } = await adminClient()
    .from("tests")
    .select("*")
    .gte("date", today)
    .lte("date", addDays(today, days))
    .is("done_at", null)
    .order("date")
    .order("start_time", { nullsFirst: false })
    .limit(200);
  const list = (data ?? []) as Test[];
  if (!batches) return list;
  const ids = new Set(batches.map((b) => b.id));
  const classes = new Set(batches.map((b) => `${b.board}${b.class}`));
  return list.filter((t) => (t.batch_id ? ids.has(t.batch_id) : classes.has(`${t.board}${t.class}`)));
}

export type ClassTop = { board: string; cls: number; test: Test; top: { student: StudentLite; score: number; pct: number | null }[] };

/** Top 5 of the latest marked test in every class. */
export async function classTop5(today: string, students: StudentLite[]): Promise<ClassTop[]> {
  const db = adminClient();
  const { data: tests } = await db.from("tests").select("*").lte("date", today).order("date", { ascending: false }).limit(150);
  const list = (tests ?? []) as Test[];
  if (!list.length) return [];
  const marks = await fetchAll<{ test_id: string; student_id: string; score: number | null; absent: boolean }>(() =>
    db.from("marks").select("test_id, student_id, score, absent").in("test_id", list.map((t) => t.id)).eq("absent", false).order("test_id").order("student_id"),
  );
  const byTest = new Map<string, { student_id: string; score: number }[]>();
  for (const m of marks) {
    if (m.score === null) continue;
    byTest.set(m.test_id, [...(byTest.get(m.test_id) ?? []), { student_id: m.student_id, score: Number(m.score) }]);
  }
  const byId = new Map(students.map((s) => [s.id, s]));
  const done = new Set<string>();
  const out: ClassTop[] = [];
  for (const t of list) {
    const key = `${t.board}${t.class}`;
    if (done.has(key)) continue;
    const rows = (byTest.get(t.id) ?? []).filter((r) => byId.has(r.student_id));
    if (!rows.length) continue;
    done.add(key);
    rows.sort((a, b) => b.score - a.score);
    out.push({
      board: t.board,
      cls: t.class,
      test: t,
      top: rows.slice(0, 5).map((r) => ({
        student: byId.get(r.student_id)!,
        score: r.score,
        pct: t.max_marks ? Math.round((r.score / Number(t.max_marks)) * 100) : null,
      })),
    });
  }
  return out.sort((a, b) => a.board.localeCompare(b.board) || a.cls - b.cls);
}
