"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { can, canSeeBatch, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { activeUsersWithRole, notify } from "@/lib/notify";
import { attemptsSince, outstandingFor } from "@/lib/fees-data";
import { CALL_OUTCOME_LABEL } from "@/lib/fees";
import { monthStart, rupees, todayIst } from "@/lib/format";
import type { ActionResult } from "../fees/ActionForm";

const Input = z.object({
  studentId: z.string().uuid(),
  guardianId: z.string().uuid(),
  outcome: z.enum(["will_pay_today", "promised_date", "not_connected", "wrong_number", "needs_admin"]),
  followUpDate: z.string().optional(),
  note: z.string().max(1000).optional(),
});

/** "Call done": saves the outcome, counts the attempt, escalates "Needs admin". */
export async function logCall(_prev: ActionResult, formData: FormData): Promise<ActionResult> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "fees.view")) return { ok: false, message: "No access." };
  const parsed = Input.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { ok: false, message: "Choose how the call went." };
  const { studentId, guardianId, outcome } = parsed.data;
  const note = parsed.data.note?.trim() || null;
  const today = todayIst();
  let followUp: string | null = null;
  if (outcome === "promised_date") {
    followUp = parsed.data.followUpDate ?? "";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(followUp)) return { ok: false, message: "Choose the date the parent promised." };
    if (followUp < today) return { ok: false, message: "The promised date cannot be in the past." };
  }

  const db = adminClient();
  const [{ data: student }, { data: guardian }] = await Promise.all([
    db.from("students").select("id, name, code, batch_id").eq("id", studentId).maybeSingle(),
    db.from("guardians").select("name, relation, mobile").eq("id", guardianId).eq("student_id", studentId).maybeSingle(),
  ]);
  if (!student || !canSeeBatch(viewer, student.batch_id)) return { ok: false, message: "Student not found." };
  if (!guardian) return { ok: false, message: "Choose the number you called." };

  const due = await outstandingFor(studentId, today);
  const month = due.months[0] ?? monthStart(today);
  const attempt = (await attemptsSince(studentId, month)) + 1;

  const { error } = await db.from("call_log").insert({
    student_id: studentId,
    month,
    guardian_name: guardian.name ?? guardian.relation,
    guardian_mobile: guardian.mobile,
    called_by: viewer.user.id,
    outcome,
    follow_up_date: followUp,
    note,
    attempt_no: attempt,
  });
  if (error) return { ok: false, message: "Could not save the call. Please try again." };

  const stages = [{ student_id: studentId, month, stage: "called", created_by: viewer.user.id }];
  if (outcome === "needs_admin") {
    stages.push({ student_id: studentId, month, stage: "escalated", created_by: viewer.user.id });
    const admins = await activeUsersWithRole(["admin"]);
    await notify(
      admins.map((a) => ({
        userId: a.id,
        kind: "escalation",
        title: `Needs admin: ${student.name}`,
        body: `${rupees(due.total)} pending. ${viewer.user.name} called (attempt ${attempt})${note ? `: ${note}` : "."}`,
        link: `/calls?student=${studentId}`,
        dedupeKey: `escalation:${studentId}:${today}`,
      })),
    );
  }
  await db.from("fee_reminders").insert(stages);
  // The day-after-due call task for this student is done once a call is logged.
  await db
    .from("call_tasks")
    .update({ status: "done", done_at: new Date().toISOString(), done_by: viewer.user.id })
    .eq("student_id", studentId)
    .eq("status", "open");
  await logActivity(viewer, "call.log", { type: "student", id: studentId }, { outcome, attempt, follow_up_date: followUp });
  revalidatePath("/calls");
  revalidatePath(`/fees/${studentId}`);
  return { ok: true, message: `Saved: ${CALL_OUTCOME_LABEL[outcome]} (call attempt ${attempt}).` };
}
