// Home search (spec §7): by student ID (current or earlier), name, parent's
// mobile number, or class. Pure parsing here; the database part is below.

import { parseStudentId, type Board } from "./ids";

export type SearchQuery =
  | { kind: "id"; code: string }
  | { kind: "mobile"; digits: string }
  | { kind: "class"; board: Board | null; cls: number }
  | { kind: "name"; text: string };

/** Reads what was typed. Null when there is nothing to search for. */
export function parseSearchQuery(raw: string): SearchQuery | null {
  const text = raw.trim().replace(/\s+/g, " ");
  if (!text) return null;

  const id = parseStudentId(text);
  if (id) return { kind: "id", code: text.replace(/\s+/g, "").toUpperCase() };

  // Class: "9", "class 9", "MP9", "CB 12", "cbse 10", "mp board 9"
  const cls = /^(?:(cb|cbse|mp|mp ?board)\s*)?(?:class\s*)?(6|7|8|9|10|11|12)(?:th)?$/i.exec(text);
  if (cls) {
    const b = cls[1]?.toLowerCase().replace(/\s/g, "");
    const board: Board | null = !b ? null : b.startsWith("cb") ? "CB" : "MP";
    return { kind: "class", board, cls: Number(cls[2]) };
  }

  // Mobile (full or part): 5 or more digits, maybe with +91, spaces, dashes.
  if (/^\+?[\d\s-]{5,}$/.test(text)) {
    let digits = text.replace(/\D/g, "");
    if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
    if (digits.length === 11 && digits.startsWith("0")) digits = digits.slice(1);
    if (digits.length >= 5 && digits.length <= 10) return { kind: "mobile", digits };
    return null;
  }

  if (text.length < 2) return null;
  return { kind: "name", text };
}

export const SEARCH_EXAMPLES = ["CB12-087-26", "Rahul", "MP9", "98765"];
