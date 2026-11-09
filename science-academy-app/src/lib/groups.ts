// Groups (spec §14): pure rules, shared by the server and the tests.

import type { PermissionKey, Role } from "./permissions";
import type { GroupKind, MessageType } from "./types";

export const POST_TYPES: { type: Exclude<MessageType, "chat">; label: string }[] = [
  { type: "notice", label: "Notice" },
  { type: "timetable", label: "Timetable" },
  { type: "test", label: "Test" },
];

export const MESSAGE_TYPE_LABEL: Record<MessageType, string> = {
  chat: "Message",
  notice: "Notice",
  timetable: "Timetable",
  test: "Test",
};

export const BATCH_GROUP_WARNING = "Every parent in this batch can read this. Never write a student's name with a fee amount.";
export const FACULTY_GROUP_HINT = "Do not share parents' numbers or fee details here.";
export const FEE_BLOCKED_ERROR =
  "This looks like a fee message. Fee messages never go in a batch group: every parent can read it. Fee reminders go to each parent privately from the Fees screen.";

type Who = { role: Role; perms: Record<PermissionKey, boolean> };

/**
 * Does this text look like fee details? Money (₹ / Rs / INR / rupees with a
 * number), the word fee(s) with a number, or due / pending / balance with an
 * amount-like number (3+ digits).
 */
export function looksLikeFeeMessage(text: string): boolean {
  const t = text.toLowerCase();
  const money = /(₹|\brs\.?\s*\d|\binr\s*\d|\d[\d,]*\s*(?:\/-|rs\b|rupees?\b|inr\b)|\brupees?\b)/;
  if (money.test(t) && /\d/.test(t)) return true;
  if (/\bfees?\b/.test(t) && /\d/.test(t)) return true;
  if (/\b(due|dues|pending|balance|outstanding)\b/.test(t) && /\b\d{1,3}(,\d{2,3})+\b|\b\d{3,}\b/.test(t)) {
    // Dates like 2026 or times like 1030 alone are not amounts: need a number that is not a year.
    const nums = t.match(/\b\d[\d,]*\b/g) ?? [];
    return nums.some((n) => {
      const v = Number(n.replace(/,/g, ""));
      return v >= 100 && !(v >= 1990 && v <= 2099 && !n.includes(","));
    });
  }
  return false;
}

/** May this staff member read a group? (Parents are checked by their children's batches.) */
export function staffCanRead(who: Who, kind: GroupKind): boolean {
  if (kind === "batch") return who.role === "admin" || who.role === "management" || who.perms["groups.post_batch"];
  if (!who.perms["groups.staff_chat"]) return false;
  if (kind === "management") return who.role === "admin" || who.role === "management" || who.role === "reception";
  return who.role !== "parent";
}

/** May this person write in a group? Batch groups: only "post in batch groups". */
export function staffCanPost(who: Who, kind: GroupKind): boolean {
  if (who.role === "parent") return false;
  if (kind === "batch") return who.perms["groups.post_batch"];
  return staffCanRead(who, kind);
}

/** "Seen by 21 of 28 parents": readers among the batch's parent logins. */
export function seenSummary(readerIds: Iterable<string>, parentIds: Iterable<string>): { seen: number; total: number } {
  const parents = new Set(parentIds);
  const readers = new Set(readerIds);
  let seen = 0;
  for (const id of readers) if (parents.has(id)) seen++;
  return { seen, total: parents.size };
}

/** Ticks on your own message: 1 = sent, 2 = seen by some, 3 = seen by everyone. */
export function tickState(readers: number, audience: number): 1 | 2 | 3 {
  if (readers <= 0) return 1;
  return audience > 0 && readers >= audience ? 3 : 2;
}

/** Delete: your own message, or any message for Admin. Parents never delete. */
export function canDeleteMessage(role: Who["role"], isSender: boolean): boolean {
  if (role === "parent") return false;
  return isSender || role === "admin";
}
