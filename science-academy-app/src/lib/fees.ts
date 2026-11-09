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

/** YYYY-MM-05 for a YYYY-MM-01. */
export function dueDate(month: string): string {
  return `${month.slice(0, 8)}${String(DUE_DAY).padStart(2, "0")}`;
}

/**
 * Paid: nothing left. Partial: some paid, the rest not yet late.
 * Overdue: money left after the due date (partial payments included).
 * Pending: nothing paid, not yet late.
 */
export function feeStatus(amount: number, paid: number, month: string, today: string): FeeStatus {
  const balance = Number(amount) - Number(paid);
  if (balance <= 0) return "paid";
  if (today > dueDate(month)) return "overdue";
  return Number(paid) > 0 ? "partial" : "pending";
}

/** Days late after the due date (0 when not late). */
export function daysLate(month: string, today: string): number {
  return Math.max(0, daysBetween(dueDate(month), today));
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
