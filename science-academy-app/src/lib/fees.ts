// Fee rules (spec §1, §9): monthly fees, due on the 5th.

import { daysBetween, monthStart } from "./format";

export const DUE_DAY = 5;

export type FeeStatus = "paid" | "partial" | "pending" | "overdue";

export const FEE_STATUS_LABEL: Record<FeeStatus, string> = {
  paid: "Paid",
  partial: "Partial",
  pending: "Pending",
  overdue: "Overdue",
};

/** YYYY-MM-DD for a YYYY-MM-01 and a due day (default the 5th). */
export function dueDate(month: string, day: number = DUE_DAY): string {
  return `${month.slice(0, 8)}${String(day).padStart(2, "0")}`;
}

/** A fee row's own due date; older rows without one fall back to the 5th of their month. */
export function rowDue(row: { month: string; due_date?: string | null }): string {
  return row.due_date ? row.due_date.slice(0, 10) : dueDate(row.month);
}

/**
 * Paid: nothing left. Partial: some paid, the rest not yet late.
 * Overdue: money left after the due date (partial payments included).
 * Pending: nothing paid, not yet late.
 * `due` is the row's own due date (else the 5th of the month).
 */
export function feeStatus(amount: number, paid: number, month: string, today: string, due?: string | null): FeeStatus {
  const balance = Number(amount) - Number(paid);
  if (balance <= 0) return "paid";
  if (today > (due ? due.slice(0, 10) : dueDate(month))) return "overdue";
  return Number(paid) > 0 ? "partial" : "pending";
}

/** Days late after the due date (0 when not late). */
export function daysLate(month: string, today: string, due?: string | null): number {
  return Math.max(0, daysBetween(due ? due.slice(0, 10) : dueDate(month), today));
}

export function balanceOf(row: { amount: number; paid: number }): number {
  return Math.max(0, Number(row.amount) - Number(row.paid));
}

/** The fee month a bill is most likely for: this month. */
export function currentFeeMonth(today: string): string {
  return monthStart(today);
}

export const PAYMENT_MODE_LABEL = { upi: "UPI", bank: "Bank transfer", cash: "Cash" } as const;

export const CALL_OUTCOME_LABEL = {
  will_pay_today: "Will pay today",
  promised_date: "Promised a date",
  not_connected: "Not connected",
  wrong_number: "Wrong number",
  needs_admin: "Needs admin",
} as const;

/** Bill numbers: SA-26-0412. */
export function invoiceNumber(series: number, seq: number): string {
  return `SA-${String(series % 100).padStart(2, "0")}-${String(seq).padStart(4, "0")}`;
}

/** Amount in words for the bill: "Two thousand five hundred rupees only". */
export function rupeesInWords(amount: number): string {
  const n = Math.round(Number(amount));
  if (n === 0) return "Zero rupees only";
  const ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"];
  const tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"];
  const two = (x: number) => (x < 20 ? ones[x] : `${tens[Math.floor(x / 10)]}${x % 10 ? ` ${ones[x % 10]}` : ""}`);
  const three = (x: number) => {
    const h = Math.floor(x / 100);
    const r = x % 100;
    return [h ? `${ones[h]} hundred` : "", r ? two(r) : ""].filter(Boolean).join(" ");
  };
  const parts: string[] = [];
  const crore = Math.floor(n / 1_00_00_000);
  const lakh = Math.floor((n % 1_00_00_000) / 1_00_000);
  const thousand = Math.floor((n % 1_00_000) / 1000);
  const rest = n % 1000;
  if (crore) parts.push(`${two(crore)} crore`);
  if (lakh) parts.push(`${two(lakh)} lakh`);
  if (thousand) parts.push(`${two(thousand)} thousand`);
  if (rest) parts.push(three(rest));
  const text = parts.join(" ");
  return `${text.charAt(0).toUpperCase()}${text.slice(1)} rupees only`;
}

// ---------------------------------------------------------------------------
// Fee plans (chosen at registration)
// ---------------------------------------------------------------------------

export type FeePlan = "monthly" | "one_time" | "installments" | "manual";

export const FEE_PLAN_LABEL: Record<FeePlan, string> = {
  monthly: "Monthly",
  one_time: "One time (full payment)",
  installments: "Installments",
  manual: "Manual schedule",
};

export type Installment = { due_date: string; amount: number; label: string };

const r2 = (n: number) => Math.round(n * 100) / 100;

/** Adds months to a YYYY-MM-DD, keeping the day (capped at the month's end). */
export function addMonthsToDate(date: string, n: number): string {
  const [y, m, d] = date.split("-").map(Number);
  const total = y * 12 + (m - 1) + n;
  const ny = Math.floor(total / 12);
  const nm = (total % 12) + 1;
  const last = new Date(Date.UTC(ny, nm, 0)).getUTCDate();
  return `${ny}-${String(nm).padStart(2, "0")}-${String(Math.min(d, last)).padStart(2, "0")}`;
}

/**
 * Splits a total into equal installments (whole rupees; the first one takes
 * the remainder), the first on `firstDue`, then every `gapMonths` months.
 */
export function makeInstallments(total: number, count: number, firstDue: string, gapMonths = 1): Installment[] {
  const n = Math.max(1, Math.min(24, Math.floor(count)));
  const base = Math.floor(total / n);
  const first = r2(total - base * (n - 1));
  return Array.from({ length: n }, (_, i) => ({
    due_date: addMonthsToDate(firstDue, i * Math.max(1, gapMonths)),
    amount: i === 0 ? first : base,
    label: `Installment ${i + 1} of ${n}`,
  }));
}

/** Checks a schedule before saving. One installment per month (fee rows are kept per month). */
export function checkSchedule(rows: Installment[]): string | null {
  if (!rows.length) return "Add at least one payment.";
  const months = new Set<string>();
  for (const [i, r] of rows.entries()) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.due_date)) return `Payment ${i + 1}: choose a date.`;
    if (!(Number(r.amount) > 0)) return `Payment ${i + 1}: enter the amount.`;
    const m = r.due_date.slice(0, 7);
    if (months.has(m)) return "Keep one payment per month (two payments fall in the same month).";
    months.add(m);
  }
  return null;
}

export function scheduleTotal(rows: { amount: number }[]): number {
  return r2(rows.reduce((a, r) => a + Number(r.amount || 0), 0));
}
