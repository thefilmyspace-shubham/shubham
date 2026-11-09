"use server";

import { revalidatePath } from "next/cache";
import { can, canSeeBatch, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { notify, parentUserOf } from "@/lib/notify";
import { callList, outstandingFor } from "@/lib/fees-data";
import { monthLabel, rupees, todayIst } from "@/lib/format";
import type { ActionResult } from "./ActionForm";

const UUID = /^[0-9a-f-]{36}$/i;

/**
 * Sends one PRIVATE fee reminder to the parent's own login (never to a batch
 * group) and records it in the reminder chain. Once per student per day.
 */
async function remindOne(studentId: string, staffUserId: string, today: string): Promise<{ ok: boolean; message: string }> {
  const db = adminClient();
  const { data: student } = await db.from("students").select("id, name, status, batch_id").eq("id", studentId).maybeSingle();
  if (!student || student.status !== "active") return { ok: false, message: "Student not found." };
  const due = await outstandingFor(studentId, today);
  if (due.total <= 0) return { ok: false, message: "Nothing is pending for this student." };
  const parent = await parentUserOf(studentId);
  if (!parent) return { ok: false, message: "No login number for this student." };
  const months = due.months.map(monthLabel).join(", ");
  await notify([
    {
      userId: parent.id,
      kind: "fee_reminder",
      title: `Fee reminder: ${student.name}`,
      body: `${rupees(due.total)} is pending (${months}). Fees are due on the 5th of every month. Tap to see how to pay.`,
      link: "/parent/fees",
      dedupeKey: `fee-reminder:${studentId}:${today}`,
    },
  ]);
  await db.from("fee_reminders").insert({ student_id: studentId, month: due.months[0], stage: "reminded", created_by: staffUserId });
  return { ok: true, message: `Reminder sent to the parent (${rupees(due.total)}).` };
}

export async function sendFeeReminder(_prev: ActionResult, formData: FormData): Promise<ActionResult> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "fees.view")) return { ok: false, message: "No access." };
  const studentId = String(formData.get("studentId") ?? "");
  if (!UUID.test(studentId)) return { ok: false, message: "Student not found." };
  const { data: s } = await adminClient().from("students").select("batch_id").eq("id", studentId).maybeSingle();
  if (!s || !canSeeBatch(viewer, s.batch_id)) return { ok: false, message: "Student not found." };
  const today = todayIst();
  const result = await remindOne(studentId, viewer.user.id, today);
  if (result.ok) {
    await logActivity(viewer, "fee.remind", { type: "student", id: studentId }, { count: 1 });
    revalidatePath(`/fees/${studentId}`);
  }
  return result;
}

/** Private reminders to every parent with an overdue fee. */
export async function remindAllOverdue(): Promise<ActionResult> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "fees.view")) return { ok: false, message: "No access." };
  const today = todayIst();
  const list = (await callList(today)).filter((e) => canSeeBatch(viewer, e.student.batch_id));
  let sent = 0;
  for (const e of list) {
    const r = await remindOne(e.studentId, viewer.user.id, today);
    if (r.ok) sent++;
  }
  await logActivity(viewer, "fee.remind", { type: "bulk" }, { count: sent, overdue: list.length });
  revalidatePath("/fees");
  return { ok: true, message: sent ? `Reminders sent to ${sent} parent${sent === 1 ? "" : "s"}.` : "No overdue parents to remind." };
}
