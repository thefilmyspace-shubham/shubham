"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { can, canSeeBatch, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { activeUsersWithRole, notify } from "@/lib/notify";
import { attemptsSince, outstandingFor } from "@/lib/fees-data";
import { all } from "@/lib/i18n";
import { getT } from "@/lib/i18n/server";
import { monthStart, rupees, todayIst } from "@/lib/format";
import type { ActionResult } from "../fees/ActionForm";

const Input = z.object({
  studentId: z.string().uuid(),
  guardianId: z.string().uuid(),
  outcome: z.enum(["will_pay_today", "promised_date", "not_connected", "wrong_number", "needs_admin"]),
  followUpDate: z.string().optional(),
  moveDue: z.string().optional(),
  note: z.string().max(1000).optional(),
});

/** "Call done": saves the outcome, counts the attempt, escalates "Needs admin". */
export async function logCall(_prev: ActionResult, formData: FormData): Promise<ActionResult> {
  const viewer = await staffForApi();
  const { t } = await getT();
  if (!viewer || !can(viewer, "fees.view")) return { ok: false, message: t("fees.msg.noAccess") };
  const parsed = Input.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { ok: false, message: t("fees.cd.err.outcome") };
  const { studentId, guardianId, outcome } = parsed.data;
  const note = parsed.data.note?.trim() || null;
  const today = todayIst();
  let followUp: string | null = null;
  if (outcome === "promised_date") {
    followUp = parsed.data.followUpDate ?? "";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(followUp)) return { ok: false, message: t("fees.cd.err.date") };
    if (followUp < today) return { ok: false, message: t("fees.cd.err.past") };
  }

  const db = adminClient();
  const [{ data: student }, { data: guardian }] = await Promise.all([
    db.from("students").select("id, name, code, batch_id").eq("id", studentId).maybeSingle(),
    db.from("guardians").select("name, relation, mobile").eq("id", guardianId).eq("student_id", studentId).maybeSingle(),
  ]);
  if (!student || !canSeeBatch(viewer, student.batch_id)) return { ok: false, message: t("fees.msg.studentNotFound") };
  if (!guardian) return { ok: false, message: t("fees.cd.err.number") };

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
  if (error) return { ok: false, message: t("fees.cd.err.save") };

  const stages = [{ student_id: studentId, month, stage: "called", created_by: viewer.user.id }];
  if (outcome === "needs_admin") {
    stages.push({ student_id: studentId, month, stage: "escalated", created_by: viewer.user.id });
    const admins = await activeUsersWithRole(["admin"]);
    await notify(
      admins.map((a) => ({
        userId: a.id,
        kind: "escalation",
        title: all("fees.notify.escTitle", { name: student.name }),
        body: all("fees.notify.escBody", { amount: rupees(due.total), staff: viewer.user.name, n: attempt, note: note ? `: ${note}` : "." }),
        link: `/calls?student=${studentId}`,
        dedupeKey: `escalation:${studentId}:${today}`,
      })),
    );
  }
  await db.from("fee_reminders").insert(stages);
  // Promised a date: the overdue fees of this student are now due on that date.
  let movedDue = 0;
  if (outcome === "promised_date" && followUp && parsed.data.moveDue === "on" && can(viewer, "bills.create")) {
    const { data: late } = await db.from("fees_ledger").select("id, amount, paid, due_date, month").eq("student_id", studentId);
    const ids = ((late ?? []) as { id: string; amount: number; paid: number; due_date: string | null; month: string }[])
      .filter((r) => Number(r.amount) - Number(r.paid) > 0 && (r.due_date ?? `${r.month.slice(0, 8)}05`) <= today)
      .map((r) => r.id);
    if (ids.length) {
      await db.from("fees_ledger").update({ due_date: followUp }).in("id", ids);
      movedDue = ids.length;
    }
  }
  // The day-after-due call task for this student is done once a call is logged.
  await db
    .from("call_tasks")
    .update({ status: "done", done_at: new Date().toISOString(), done_by: viewer.user.id })
    .eq("student_id", studentId)
    .eq("status", "open");
  await logActivity(viewer, "call.log", { type: "student", id: studentId }, { outcome, attempt, follow_up_date: followUp, due_dates_moved: movedDue });
  revalidatePath("/calls");
  revalidatePath(`/fees/${studentId}`);
  return { ok: true, message: t("fees.cd.saved", { outcome: t(`fees.call.${outcome}`), n: attempt }) };
}
