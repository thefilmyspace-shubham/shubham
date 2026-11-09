// Student ID rules (spec §4): BOARD CLASS - ROLL - SESSION YEAR, e.g. MP9-025-26.

export type Board = "CB" | "MP";
export const BOARDS: Board[] = ["CB", "MP"];
export const CLASSES = [6, 7, 8, 9, 10, 11, 12] as const;

export function boardName(board: Board | string): string {
  return board === "CB" ? "CBSE" : "MP Board";
}

/** Roll is 3 digits zero padded; from 1000 it simply has 4 digits. */
export function formatRoll(roll: number): string {
  return roll < 1000 ? String(roll).padStart(3, "0") : String(roll);
}

/** Same rule as public.format_student_id in the database. */
export function formatStudentId(board: Board | string, cls: number, roll: number, session: number): string {
  return `${board}${cls}-${formatRoll(roll)}-${String(session % 100).padStart(2, "0")}`;
}

/** The academic session starts in April: Nov 2026 → 26 (2026-27), Feb 2027 → 26. */
export function sessionYearFor(date: Date): number {
  const ist = toIst(date);
  const y = ist.getUTCFullYear();
  const m = ist.getUTCMonth() + 1;
  return (m >= 4 ? y : y - 1) % 100;
}

/** 26 → "2026-27". */
export function sessionLabel(session: number): string {
  const start = 2000 + (session % 100);
  return `${start}-${String((start + 1) % 100).padStart(2, "0")}`;
}

/** Date shifted to India time, read with getUTC* methods. */
export function toIst(date: Date): Date {
  return new Date(date.getTime() + 330 * 60_000);
}

const ID_RE = /^(CB|MP)(6|7|8|9|10|11|12)-(\d{3,})-(\d{2})$/i;

export type ParsedId = { board: Board; cls: number; roll: number; session: number };

/** Reads "mp9-025-26" (any case, spaces ignored). Null when it is not an ID. */
export function parseStudentId(text: string): ParsedId | null {
  const m = ID_RE.exec(text.replace(/\s+/g, ""));
  if (!m) return null;
  return { board: m[1].toUpperCase() as Board, cls: Number(m[2]), roll: Number(m[3]), session: Number(m[4]) };
}

/** The ID after a year-end promotion: class + 1, session + 1, same roll. */
export function promotedId(id: ParsedId): ParsedId | null {
  if (id.cls >= 12) return null;
  return { ...id, cls: id.cls + 1, session: (id.session + 1) % 100 };
}

/** Indian mobile: 10 digits starting 6-9. Accepts +91 / 0 / spaces. */
export function normalizeMobile(text: string): string | null {
  let digits = text.replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
  if (digits.length === 11 && digits.startsWith("0")) digits = digits.slice(1);
  return /^[6-9]\d{9}$/.test(digits) ? digits : null;
}

/** 98765 43210 */
export function formatMobile(mobile: string): string {
  return mobile.length === 10 ? `${mobile.slice(0, 5)} ${mobile.slice(5)}` : mobile;
}

/** 98•••••210, for screens that should not show the full number. */
export function maskMobile(mobile: string): string {
  return mobile.length === 10 ? `${mobile.slice(0, 2)}••••••${mobile.slice(-2)}` : "••••";
}

/** Staff IDs: AD-01, MG-01, RC-01, FC-01. */
export function parseStaffId(text: string): string | null {
  const m = /^(AD|MG|RC|FC)-?(\d{1,4})$/i.exec(text.trim());
  return m ? `${m[1].toUpperCase()}-${m[2].padStart(2, "0")}` : null;
}
