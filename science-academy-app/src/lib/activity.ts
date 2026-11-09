import "server-only";
import { adminClient } from "./supabase/admin";
import { actorLabel, type Viewer } from "./auth";

/**
 * Writes one line to the activity log (append-only). Used for every
 * sensitive action: fees, bills, attendance edits, access changes,
 * promotions, exports, AI actions, registrations.
 */
export async function logActivity(
  viewer: Viewer | null,
  action: string,
  entity?: { type: string; id?: string | null },
  details: Record<string, unknown> = {},
): Promise<void> {
  const { error } = await adminClient()
    .from("activity_log")
    .insert({
      actor_id: viewer?.user.id ?? null,
      actor_label: viewer ? actorLabel(viewer.user) : "System",
      action,
      entity: entity?.type ?? null,
      entity_id: entity?.id ?? null,
      details,
    });
  if (error) console.error("activity log failed", action, error.message);
}

/** Readable names for the activity log screen. */
export const ACTION_LABEL: Record<string, string> = {
  "auth.login": "Logged in",
  "auth.logout": "Logged out",
  "student.register": "Registered a student",
  "student.draft": "Saved a draft registration",
  "student.edit": "Edited a student",
  "student.left": "Marked a student as left",
  "bill.create": "Made a bill",
  "bill.cancel": "Cancelled a bill",
  "bill.email": "Emailed a bill",
  "bill.print": "Printed a bill",
  "fee.edit": "Changed a fee",
  "call.log": "Logged a call",
  "fee.remind": "Sent fee reminders",
  "attendance.save": "Saved attendance",
  "attendance.correct": "Corrected attendance",
  "attendance.alert": "Sent an attendance alert to a parent",
  "marks.save": "Saved marks",
  "test.save": "Saved a test",
  "test.delete": "Deleted a test",
  "timetable.save": "Changed the timetable",
  "group.post": "Posted in a batch group",
  "access.role": "Changed role access",
  "access.reset": "Reset access to defaults",
  "access.person": "Changed a person's access",
  "staff.add": "Added a staff member",
  "staff.edit": "Changed a staff member's details",
  "staff.suspend": "Suspended a login",
  "staff.restore": "Restored a login",
  "staff.logout_all": "Logged a person out everywhere",
  "batch.save": "Saved a batch",
  "promotion.run": "Ran year-end promotion",
  "export.backup": "Downloaded a backup",
  "export.ranks": "Downloaded a ranking PDF",
  "ai.action": "AI action",
};
