import "server-only";
import QRCode from "qrcode";
import { adminClient } from "./supabase/admin";
import { feeStatus, balanceOf, type FeeStatus } from "./fees";
import { addMonths, monthStart } from "./format";
import { orderCallList, overdueSummary, type CallItem } from "./billing-calc";
import type { CallLogRow, CallOutcome, Guardian, Invoice, LedgerRow, Student } from "./types";

type StudentLite = Pick<Student, "id" | "name" | "code" | "board" | "current_class" | "batch_id" | "monthly_fee" | "email" | "status">;
const STUDENT_COLS = "id, name, code, board, current_class, batch_id, monthly_fee, email, status";

const num = (v: unknown) => Number(v ?? 0);

function toLedger(r: Record<string, unknown>): LedgerRow {
  return { id: String(r.id), student_id: String(r.student_id), month: String(r.month), amount: num(r.amount), paid: num(r.paid) };
}

/**
 * Makes this month's fee row for every active student with a monthly fee.
 * Safe to run again: rows that exist are left as they are. Returns how many were made.
 */
export async function ensureLedgerForMonth(month: string): Promise<number> {
  const m = monthStart(month);
  const db = adminClient();
  const { data: students } = await db.from("students").select("id, monthly_fee").eq("status", "active").gt("monthly_fee", 0);
  const rows = ((students ?? []) as { id: string; monthly_fee: number }[]).map((s) => ({
    student_id: s.id,
    month: m,
    amount: num(s.monthly_fee),
  }));
  if (!rows.length) return 0;
  let made = 0;
  for (let i = 0; i < rows.length; i += 500) {
    const { data, error } = await db
      .from("fees_ledger")
      .upsert(rows.slice(i, i + 500), { onConflict: "student_id,month", ignoreDuplicates: true })
      .select("id");
    if (error) throw new Error(`ledger rows failed: ${error.message}`);
    made += data?.length ?? 0;
  }
  return made;
}

export type FeeListRow = {
  student: StudentLite;
  ledger: LedgerRow;
  status: FeeStatus;
  balance: number;
};

/** Every fee row of one month with its student and status. */
export async function feeListForMonth(month: string, today: string): Promise<FeeListRow[]> {
  const db = adminClient();
  const { data: ledger } = await db.from("fees_ledger").select("*").eq("month", month);
  const rows = ((ledger ?? []) as Record<string, unknown>[]).map(toLedger);
  if (!rows.length) return [];
  const students = await studentsById(rows.map((r) => r.student_id));
  return rows
    .filter((r) => students.has(r.student_id))
    .map((r) => ({
      student: students.get(r.student_id)!,
      ledger: r,
      status: feeStatus(r.amount, r.paid, r.month, today),
      balance: balanceOf(r),
    }))
    .sort((a, b) => a.student.name.localeCompare(b.student.name));
}

export async function studentsById(ids: string[]): Promise<Map<string, StudentLite>> {
  const map = new Map<string, StudentLite>();
  const unique = [...new Set(ids)];
  const db = adminClient();
  for (let i = 0; i < unique.length; i += 300) {
    const { data } = await db.from("students").select(STUDENT_COLS).in("id", unique.slice(i, i + 300));
    for (const s of (data ?? []) as StudentLite[]) map.set(s.id, { ...s, monthly_fee: num(s.monthly_fee) });
  }
  return map;
}

export async function guardiansOf(studentIds: string[]): Promise<Map<string, Guardian[]>> {
  const map = new Map<string, Guardian[]>();
  if (!studentIds.length) return map;
  const db = adminClient();
  const unique = [...new Set(studentIds)];
  for (let i = 0; i < unique.length; i += 300) {
    const { data } = await db.from("guardians").select("*").in("student_id", unique.slice(i, i + 300));
    for (const g of (data ?? []) as Guardian[]) {
      const list = map.get(g.student_id) ?? [];
      list.push(g);
      map.set(g.student_id, list);
    }
  }
  // Login number first, then father, mother, guardian, alternate.
  const order = { father: 1, mother: 2, guardian: 3, alternate: 4 } as const;
  for (const list of map.values()) {
    list.sort((a, b) => Number(b.is_login_number) - Number(a.is_login_number) || order[a.relation] - order[b.relation]);
  }
  return map;
}

export type StudentFeeDetail = {
  student: StudentLite;
  ledger: (LedgerRow & { status: FeeStatus; balance: number })[];
  invoices: Invoice[];
  calls: CallLogRow[];
  reminders: { id: string; month: string; stage: "reminded" | "called" | "escalated"; created_by: string | null; created_at: string }[];
  guardians: Guardian[];
};

export async function studentFeeDetail(studentId: string, today: string): Promise<StudentFeeDetail | null> {
  const db = adminClient();
  const { data: student } = await db.from("students").select(STUDENT_COLS).eq("id", studentId).maybeSingle<StudentLite>();
  if (!student) return null;
  const [{ data: ledger }, { data: invoices }, { data: calls }, { data: reminders }, guardians] = await Promise.all([
    db.from("fees_ledger").select("*").eq("student_id", studentId).order("month", { ascending: false }),
    db.from("invoices").select("*").eq("student_id", studentId).order("created_at", { ascending: false }),
    db.from("call_log").select("*").eq("student_id", studentId).order("created_at", { ascending: false }),
    db.from("fee_reminders").select("*").eq("student_id", studentId).order("created_at", { ascending: false }).limit(100),
    guardiansOf([studentId]),
  ]);
  return {
    student: { ...student, monthly_fee: num(student.monthly_fee) },
    ledger: ((ledger ?? []) as Record<string, unknown>[]).map(toLedger).map((r) => ({
      ...r,
      status: feeStatus(r.amount, r.paid, r.month, today),
      balance: balanceOf(r),
    })),
    invoices: ((invoices ?? []) as Invoice[]).map(normalizeInvoice),
    calls: (calls ?? []) as CallLogRow[],
    reminders: (reminders ?? []) as StudentFeeDetail["reminders"],
    guardians: guardians.get(studentId) ?? [],
  };
}

export function normalizeInvoice(i: Invoice): Invoice {
  return {
    ...i,
    fee_amount: num(i.fee_amount),
    paid_before: num(i.paid_before),
    received: num(i.received),
    balance_after: num(i.balance_after),
  };
}

export async function getInvoice(id: string): Promise<Invoice | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const { data } = await adminClient().from("invoices").select("*").eq("id", id).maybeSingle<Invoice>();
  return data ? normalizeInvoice(data) : null;
}

/** Ledger of one student and month (fee, paid so far) and the bills already made for it. */
export async function monthPayments(studentId: string, month: string): Promise<{ amount: number | null; paid: number; invoices: Invoice[] }> {
  const db = adminClient();
  const [{ data: row }, { data: invoices }] = await Promise.all([
    db.from("fees_ledger").select("*").eq("student_id", studentId).eq("month", month).maybeSingle(),
    db.from("invoices").select("*").eq("student_id", studentId).eq("month", month).order("created_at"),
  ]);
  return {
    amount: row ? num(row.amount) : null,
    paid: row ? num(row.paid) : 0,
    invoices: ((invoices ?? []) as Invoice[]).map(normalizeInvoice),
  };
}

export type CallListEntry = CallItem & {
  student: StudentLite;
  guardians: Guardian[];
  lastCallAt: string | null;
  lastNote: string | null;
};

/**
 * Parents to call: every student with money left after a due date, longest
 * overdue first, promises due today on top. Attempts count calls made since
 * the oldest unpaid month began.
 */
export async function callList(today: string): Promise<CallListEntry[]> {
  const db = adminClient();
  const current = monthStart(today);
  const from = addMonths(current, -24);
  const all: LedgerRow[] = [];
  for (let offset = 0; ; offset += 1000) {
    const { data } = await db
      .from("fees_ledger")
      .select("*")
      .lte("month", current)
      .gte("month", from)
      .order("id")
      .range(offset, offset + 999);
    const page = ((data ?? []) as Record<string, unknown>[]).map(toLedger);
    all.push(...page);
    if (page.length < 1000) break;
  }
  const byStudent = new Map<string, LedgerRow[]>();
  for (const r of all) {
    if (r.amount - r.paid <= 0) continue;
    const list = byStudent.get(r.student_id) ?? [];
    list.push(r);
    byStudent.set(r.student_id, list);
  }
  const summaries = new Map<string, NonNullable<ReturnType<typeof overdueSummary>>>();
  for (const [id, rows] of byStudent) {
    const s = overdueSummary(rows, today);
    if (s) summaries.set(id, s);
  }
  const ids = [...summaries.keys()];
  if (!ids.length) return [];
  const [students, guardians] = await Promise.all([studentsById(ids), guardiansOf(ids)]);

  const calls: CallLogRow[] = [];
  for (let i = 0; i < ids.length; i += 300) {
    const { data } = await db
      .from("call_log")
      .select("*")
      .in("student_id", ids.slice(i, i + 300))
      .gte("created_at", `${from}T00:00:00Z`)
      .order("created_at", { ascending: false });
    calls.push(...((data ?? []) as CallLogRow[]));
  }
  const callsBy = new Map<string, CallLogRow[]>();
  for (const c of calls) {
    const list = callsBy.get(c.student_id) ?? [];
    list.push(c);
    callsBy.set(c.student_id, list);
  }

  const entries: CallListEntry[] = [];
  for (const id of ids) {
    const student = students.get(id);
    if (!student || student.status !== "active") continue;
    const sum = summaries.get(id)!;
    const mine = (callsBy.get(id) ?? []).filter((c) => c.created_at.slice(0, 10) >= sum.oldestMonth);
    const last = mine[0] ?? null;
    entries.push({
      studentId: id,
      oldestMonth: sum.oldestMonth,
      totalDue: sum.totalDue,
      daysLate: sum.daysLate,
      attempts: mine.length,
      lastOutcome: (last?.outcome as CallOutcome | undefined) ?? null,
      followUpDate: last?.follow_up_date ?? null,
      lastCallAt: last?.created_at ?? null,
      lastNote: last?.note ?? null,
      student,
      guardians: guardians.get(id) ?? [],
    });
  }
  return orderCallList(entries, today);
}

/** Calls already made for a student's current dues (for attempt numbers). */
export async function attemptsSince(studentId: string, since: string): Promise<number> {
  const { count } = await adminClient()
    .from("call_log")
    .select("id", { count: "exact", head: true })
    .eq("student_id", studentId)
    .gte("created_at", `${since}T00:00:00Z`);
  return count ?? 0;
}

/** Total unpaid (any month up to now) and the oldest unpaid month, for reminders. */
export async function outstandingFor(studentId: string, today: string): Promise<{ total: number; months: string[] }> {
  const { data } = await adminClient()
    .from("fees_ledger")
    .select("*")
    .eq("student_id", studentId)
    .lte("month", monthStart(today))
    .order("month");
  const rows = ((data ?? []) as Record<string, unknown>[]).map(toLedger).filter((r) => r.amount - r.paid > 0);
  return { total: rows.reduce((s, r) => s + (r.amount - r.paid), 0), months: rows.map((r) => r.month) };
}

/** Names of staff by user id, for "called by" / "made by". */
export async function staffNames(ids: (string | null)[]): Promise<Map<string, string>> {
  const unique = [...new Set(ids.filter((i): i is string => Boolean(i)))];
  const map = new Map<string, string>();
  if (!unique.length) return map;
  const { data } = await adminClient().from("users").select("id, name, staff_id").in("id", unique);
  for (const u of (data ?? []) as { id: string; name: string; staff_id: string | null }[]) {
    map.set(u.id, u.staff_id ? `${u.staff_id} ${u.name}` : u.name);
  }
  return map;
}

/** PNG data URL of a QR code. */
export async function qrDataUrl(text: string): Promise<string> {
  return QRCode.toDataURL(text, { margin: 1, width: 320, errorCorrectionLevel: "M" });
}
