// Pure billing and call-list logic (no database), shared by server pages,
// client forms and tests.

import { dueDate, daysLate } from "./fees";
import type { CallOutcome } from "./types";

export type BillPreview = {
  fee: number;
  paidBefore: number;
  balanceBefore: number;
  received: number;
  balanceAfter: number;
  error: string | null;
  /** The same reason as a dictionary key (with values), for the reader's language. */
  errorKey: "fees.bp.enterFee" | "fees.bp.feeBelowPaid" | "fees.bp.fullyPaid" | "fees.bp.enterReceived" | "fees.bp.moreThanBalance" | null;
  errorParams: Record<string, number>;
};

const round2 = (n: number) => Math.round(n * 100) / 100;

/** What the bill will say, and why it cannot be made (if so). */
export function billPreview(fee: number, paidBefore: number, received: number): BillPreview {
  const f = round2(Number(fee) || 0);
  const p = round2(Number(paidBefore) || 0);
  const r = round2(Number(received) || 0);
  const balanceBefore = Math.max(0, round2(f - p));
  let error: string | null = null;
  let errorKey: BillPreview["errorKey"] = null;
  let errorParams: Record<string, number> = {};
  if (f <= 0) [error, errorKey] = ["Enter the fee amount.", "fees.bp.enterFee"];
  else if (f < p) [error, errorKey, errorParams] = [`Fee cannot be less than what is already paid (${p}).`, "fees.bp.feeBelowPaid", { paid: p }];
  else if (balanceBefore === 0) [error, errorKey] = ["This month is already fully paid.", "fees.bp.fullyPaid"];
  else if (r <= 0) [error, errorKey] = ["Enter the amount received now.", "fees.bp.enterReceived"];
  else if (r > balanceBefore) [error, errorKey, errorParams] = [`Amount received is more than the balance (${balanceBefore}).`, "fees.bp.moreThanBalance", { balance: balanceBefore }];
  return { fee: f, paidBefore: p, balanceBefore, received: r, balanceAfter: Math.max(0, round2(balanceBefore - r)), error, errorKey, errorParams };
}

export type PaymentModeInput = "upi" | "bank" | "cash";

export function validModes(modes: string[]): modes is PaymentModeInput[] {
  return modes.length > 0 && modes.every((m) => m === "upi" || m === "bank" || m === "cash");
}

export type CallItem = {
  studentId: string;
  /** Oldest unpaid month (YYYY-MM-01). */
  oldestMonth: string;
  totalDue: number;
  daysLate: number;
  attempts: number;
  lastOutcome: CallOutcome | null;
  followUpDate: string | null;
};

export type CallBucket = "promised_due" | "escalated" | "call" | "promised_later";

/**
 * Which part of the call list a student belongs in:
 * a promise that is due today or has passed floats to the top; escalated
 * ones wait for Admin; a promise for a later date waits at the bottom.
 */
export function callBucket(item: CallItem, today: string): CallBucket {
  if (item.lastOutcome === "promised_date" && item.followUpDate) {
    return item.followUpDate <= today ? "promised_due" : "promised_later";
  }
  if (item.lastOutcome === "needs_admin") return "escalated";
  return "call";
}

const BUCKET_ORDER: Record<CallBucket, number> = { promised_due: 0, call: 1, escalated: 2, promised_later: 3 };

/** Promises due today first, then longest overdue first (bigger amount breaks ties). */
export function orderCallList<T extends CallItem>(items: T[], today: string): T[] {
  return [...items].sort(
    (a, b) =>
      BUCKET_ORDER[callBucket(a, today)] - BUCKET_ORDER[callBucket(b, today)] ||
      b.daysLate - a.daysLate ||
      b.totalDue - a.totalDue ||
      a.studentId.localeCompare(b.studentId),
  );
}

export type DueRow = { month: string; amount: number; paid: number; due_date?: string | null };

/** Unpaid months that are past their due date, oldest first. */
export function overdueMonths<T extends DueRow>(rows: T[], today: string): T[] {
  return rows
    .filter((r) => Number(r.amount) - Number(r.paid) > 0 && today > (r.due_date ? r.due_date.slice(0, 10) : dueDate(r.month)))
    .sort((a, b) => a.month.localeCompare(b.month));
}

/** Total overdue and how late the oldest month is. Null when nothing is overdue. */
export function overdueSummary(rows: DueRow[], today: string): { oldestMonth: string; totalDue: number; daysLate: number } | null {
  const late = overdueMonths(rows, today);
  if (!late.length) return null;
  const totalDue = late.reduce((s, r) => s + Math.max(0, Number(r.amount) - Number(r.paid)), 0);
  return { oldestMonth: late[0].month, totalDue: round2(totalDue), daysLate: daysLate(late[0].month, today, late[0].due_date) };
}

/** UPI payment link for the QR code. */
export function upiLink(upiId: string, amount?: number, note?: string): string {
  // UPI apps expect the VPA as is (name@bank), so pa is not percent-encoded.
  let link = `upi://pay?pa=${upiId.trim()}&pn=Science%20Academy&cu=INR`;
  if (amount && amount > 0) link += `&am=${amount.toFixed(2)}`;
  if (note) link += `&tn=${encodeURIComponent(note.slice(0, 50))}`;
  return link;
}
