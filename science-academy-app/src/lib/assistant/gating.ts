// Which assistant tools a person gets. Pure logic (unit tested): a tool only
// exists for someone who holds every permission it needs, so the AI can never
// reach data the same person could not open on the screens.

import type { PermissionKey } from "../permissions";

export const TOOL_REQUIREMENTS = {
  list_batches: [],
  find_student: ["students.view"],
  student_attendance: ["students.view"],
  student_marks: ["students.view"],
  batch_attendance_summary: ["students.view"],
  low_attendance: ["students.view"],
  list_tests: ["students.view"],
  test_results: ["ranks.view"],
  compare_batches: ["ranks.view"],
  class_toppers: ["ranks.view"],
  student_contacts: ["students.contacts"],
  fee_status: ["fees.view"],
  overdue_list: ["fees.view"],
  propose_fee_reminders: ["fees.view", "ai.act"],
} as const satisfies Record<string, readonly PermissionKey[]>;

export type ToolName = keyof typeof TOOL_REQUIREMENTS;
export const TOOL_NAMES = Object.keys(TOOL_REQUIREMENTS) as ToolName[];

/** The assistant is only open to people who may ask it. */
export function canUseAssistant(perms: Record<PermissionKey, boolean>): boolean {
  return perms["ai.ask"] === true;
}

export function toolAllowed(name: ToolName, perms: Record<PermissionKey, boolean>): boolean {
  if (!canUseAssistant(perms)) return false;
  return (TOOL_REQUIREMENTS[name] as readonly PermissionKey[]).every((k) => perms[k] === true);
}

export function toolNamesFor(perms: Record<PermissionKey, boolean>): ToolName[] {
  return TOOL_NAMES.filter((n) => toolAllowed(n, perms));
}

/** Tools that change something. Only ever proposed; a person confirms. */
export const ACTION_TOOLS: ToolName[] = ["propose_fee_reminders"];

/** Short list for the "what it can do" box, by what this person may use. */
export function capabilitiesFor(perms: Record<PermissionKey, boolean>): string[] {
  const names = new Set(toolNamesFor(perms));
  const out: string[] = [];
  if (names.has("find_student")) out.push("Find a student by name, ID (current or earlier) or class");
  if (names.has("student_attendance")) out.push("Attendance of a student or a batch, low-attendance lists");
  if (names.has("student_marks")) out.push("Test marks of a student");
  if (names.has("compare_batches")) out.push("Compare test marks of batches, with a PDF download");
  if (names.has("class_toppers")) out.push("Class toppers for a test");
  if (names.has("fee_status")) out.push("Fee status, overdue lists by class");
  if (names.has("student_contacts")) out.push("Parents' numbers of a student");
  if (names.has("propose_fee_reminders")) out.push("Send fee reminders to parents (you confirm first)");
  return out;
}

export function suggestionsFor(perms: Record<PermissionKey, boolean>): string[] {
  const names = new Set(toolNamesFor(perms));
  const out: string[] = [];
  if (names.has("student_attendance")) out.push("Attendance of CB12-087-26 this month");
  if (names.has("compare_batches")) out.push("Compare the last test of both class 10 CBSE batches");
  if (names.has("class_toppers")) out.push("Top 5 of class 9 MP Board in the latest test");
  if (names.has("low_attendance")) out.push("Who is below 75% attendance this month?");
  if (names.has("overdue_list")) out.push("Overdue fees in class 11");
  if (names.has("propose_fee_reminders")) out.push("Send reminders to all overdue parents of class 12");
  return out;
}
