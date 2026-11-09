// Pure comparison logic for the AI marksheet check (unit tested).

import type { AiCheck } from "../types";

export type MarksheetReply = { readable: boolean; name: string | null; percentage: number | null; note: string };

export type MarksheetCheck = {
  result: AiCheck;
  readName: string | null;
  readPercentage: number | null;
  note: string;
};

/** Pulls the JSON object out of the model's reply. Null when it is not valid. */
export function parseMarksheetReply(text: string): MarksheetReply | null {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    const raw = JSON.parse(text.slice(start, end + 1)) as Record<string, unknown>;
    const pct = raw.percentage === null || raw.percentage === undefined ? null : Number(raw.percentage);
    return {
      readable: raw.readable === true,
      name: typeof raw.name === "string" && raw.name.trim() ? raw.name.trim() : null,
      percentage: pct !== null && Number.isFinite(pct) ? pct : null,
      note: typeof raw.note === "string" ? raw.note.trim() : "",
    };
  } catch {
    return null;
  }
}

function tokens(name: string): string[] {
  return name
    .toLowerCase()
    .replace(/[^a-z\s.]/g, " ")
    .replace(/\./g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

/**
 * Same person? Case and spaces don't matter, word order doesn't matter, and an
 * initial ("R") matches a full word ("Rahul"). Every word of the shorter name
 * must match a word of the longer one, and at least one full word must match.
 */
export function namesMatch(a: string, b: string): boolean {
  const x = tokens(a);
  const y = tokens(b);
  if (!x.length || !y.length) return false;
  if (x.join("") === y.join("")) return true;
  const [short, long] = x.length <= y.length ? [x, y] : [y, x];
  const pool = [...long];
  let fullMatches = 0;
  for (const w of short) {
    let i = pool.indexOf(w);
    if (i >= 0) {
      if (w.length > 1) fullMatches++;
    } else if (w.length === 1) {
      i = pool.findIndex((p) => p.startsWith(w));
    } else {
      i = pool.findIndex((p) => p.length === 1 && w.startsWith(p));
    }
    if (i < 0) return false;
    pool.splice(i, 1);
  }
  return fullMatches > 0;
}

export const PERCENT_TOLERANCE = 0.5;

/** Matched / Mismatch / Can't read. Unclear reads never count as a match. */
export function compareMarksheet(reply: MarksheetReply, typedName: string, typedPercentage: number | null): MarksheetCheck {
  const base = { readName: reply.name, readPercentage: reply.percentage };
  if (!reply.readable || !reply.name || reply.percentage === null) {
    return {
      ...base,
      result: "cant_read",
      note: reply.note || "The name or percentage could not be read clearly. Please upload a better photo.",
    };
  }
  const problems: string[] = [];
  if (!namesMatch(reply.name, typedName)) problems.push(`name on marksheet is "${reply.name}"`);
  if (typedPercentage === null) problems.push("no percentage was typed");
  else if (Math.abs(reply.percentage - typedPercentage) > PERCENT_TOLERANCE) {
    problems.push(`percentage on marksheet is ${reply.percentage}% (typed ${typedPercentage}%)`);
  }
  if (problems.length) {
    const text = problems.join("; ");
    return { ...base, result: "mismatch", note: `${text.charAt(0).toUpperCase()}${text.slice(1)}.` };
  }
  return { ...base, result: "matched", note: "Name and percentage match the marksheet." };
}

export const AI_CHECK_LABEL: Record<AiCheck, string> = {
  pending: "Not checked",
  matched: "Matched",
  mismatch: "Mismatch",
  cant_read: "Can't read",
};

export const AI_CHECK_TONE: Record<AiCheck, "ok" | "danger" | "warn" | "neutral"> = {
  pending: "neutral",
  matched: "ok",
  mismatch: "danger",
  cant_read: "warn",
};
