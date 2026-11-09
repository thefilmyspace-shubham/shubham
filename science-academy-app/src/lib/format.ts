// Formatting helpers. All dates are India time (IST).

import { toIst } from "./ids";

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

/** ₹35,200 */
export function rupees(amount: number | string | null | undefined): string {
  const n = Number(amount ?? 0);
  return `₹${inr.format(Number.isFinite(n) ? n : 0)}`;
}

/** ₹1.2L / ₹35.2K for dashboard tiles. */
export function rupeesShort(amount: number): string {
  if (amount >= 1_00_00_000) return `₹${trim(amount / 1_00_00_000)}Cr`;
  if (amount >= 1_00_000) return `₹${trim(amount / 1_00_000)}L`;
  if (amount >= 1000) return `₹${trim(amount / 1000)}K`;
  return `₹${Math.round(amount)}`;
}

function trim(n: number): string {
  return n.toFixed(1).replace(/\.0$/, "");
}

/** Today's date in India as YYYY-MM-DD. */
export function todayIst(now: Date = new Date()): string {
  return toIst(now).toISOString().slice(0, 10);
}

/** First day of the month (YYYY-MM-01) for a YYYY-MM-DD or Date, in IST. */
export function monthStart(date: string | Date = new Date()): string {
  const iso = typeof date === "string" ? date : todayIst(date);
  return `${iso.slice(0, 7)}-01`;
}

/** Adds months to a YYYY-MM-01. */
export function addMonths(month: string, n: number): string {
  const [y, m] = month.split("-").map(Number);
  const total = y * 12 + (m - 1) + n;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}-01`;
}

/** Adds days to a YYYY-MM-DD. */
export function addDays(date: string, n: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "November 2026" */
export function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return `${MONTHS_LONG[m - 1]} ${y}`;
}

/** "Nov" */
export function monthShort(month: string): string {
  return MONTHS[Number(month.split("-")[1]) - 1];
}

/** "9 Nov 2026" */
export function dateLabel(date: string | null | undefined): string {
  if (!date) return "";
  const [y, m, d] = date.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** "Mon, 9 Nov" */
export function dayLabel(date: string): string {
  const d = new Date(`${date.slice(0, 10)}T00:00:00Z`);
  return `${DAYS[d.getUTCDay()]}, ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

/** 1 = Monday ... 7 = Sunday, for a YYYY-MM-DD. */
export function weekdayOf(date: string): number {
  const day = new Date(`${date}T00:00:00Z`).getUTCDay();
  return day === 0 ? 7 : day;
}

/** "4:30 PM" from an ISO timestamp, IST. */
export function timeLabel(iso: string): string {
  const d = toIst(new Date(iso));
  let h = d.getUTCHours();
  const min = String(d.getUTCMinutes()).padStart(2, "0");
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${min} ${ampm}`;
}

/** "8:00 AM" from "08:00:00". */
export function clockLabel(time: string | null | undefined): string {
  if (!time) return "";
  const [hh, mm] = time.split(":").map(Number);
  const ampm = hh >= 12 ? "PM" : "AM";
  return `${hh % 12 || 12}:${String(mm).padStart(2, "0")} ${ampm}`;
}

/** "9 Nov, 4:30 PM" */
export function dateTimeLabel(iso: string): string {
  const day = todayIst(new Date(iso));
  return `${dateLabel(day).replace(/ \d{4}$/, "")}, ${timeLabel(iso)}`;
}

/** Whole days from a to b (YYYY-MM-DD). */
export function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000);
}

export function percent(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0;
}
