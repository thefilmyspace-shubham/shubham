// Which assistant tools a person gets. Pure logic (unit tested): a tool only
// exists for someone who holds every permission it needs, so the AI can never
// reach data the same person could not open on the screens.

import type { PermissionKey } from "../permissions";
import type { TFn } from "../i18n";

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
export function capabilitiesFor(perms: Record<PermissionKey, boolean>, t: TFn): string[] {
  const names = new Set(toolNamesFor(perms));
  const out: string[] = [];
  if (names.has("find_student")) out.push(t("admin.ai.cap.find"));
  if (names.has("student_attendance")) out.push(t("admin.ai.cap.attendance"));
  if (names.has("student_marks")) out.push(t("admin.ai.cap.marks"));
  if (names.has("compare_batches")) out.push(t("admin.ai.cap.compare"));
  if (names.has("class_toppers")) out.push(t("admin.ai.cap.toppers"));
  if (names.has("fee_status")) out.push(t("admin.ai.cap.fees"));
  if (names.has("student_contacts")) out.push(t("admin.ai.cap.contacts"));
  if (names.has("propose_fee_reminders")) out.push(t("admin.ai.cap.remind"));
  return out;
}

export function suggestionsFor(perms: Record<PermissionKey, boolean>, t: TFn): string[] {
  const names = new Set(toolNamesFor(perms));
  const out: string[] = [];
  if (names.has("student_attendance")) out.push(t("admin.ai.sug.attendance"));
  if (names.has("compare_batches")) out.push(t("admin.ai.sug.compare"));
  if (names.has("class_toppers")) out.push(t("admin.ai.sug.toppers"));
  if (names.has("low_attendance")) out.push(t("admin.ai.sug.low"));
  if (names.has("overdue_list")) out.push(t("admin.ai.sug.overdue"));
  if (names.has("propose_fee_reminders")) out.push(t("admin.ai.sug.remind"));
  return out;
}
