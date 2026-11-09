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

// ---------------------------------------------------------------------------
// Payment plan and due dates (Admin and Reception: fees + bills permission)
// ---------------------------------------------------------------------------

type PlanResult = { ok: true } | { ok: false; error: string };

async function planEditor(studentId: string) {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "fees.view") || !can(viewer, "bills.create")) return null;
  if (!UUID.test(studentId)) return null;
  const { data: student } = await adminClient().from("students").select("*").eq("id", studentId).maybeSingle();
  if (!student || !canSeeBatch(viewer, student.batch_id)) return null;
  return { viewer, student };
}

const isDate = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s);
const monthOf = (d: string) => `${d.slice(0, 7)}-01`;

/** Change one payment's due date and amount (the amount cannot go below what is already paid). */
export async function updateFeeRow(rowId: string, dueDate: string, amount: number, label: string): Promise<PlanResult> {
  const db = adminClient();
  if (!UUID.test(rowId) || !isDate(dueDate)) return { ok: false, error: "Choose a date." };
  const { data: row } = await db.from("fees_ledger").select("*").eq("id", rowId).maybeSingle();
  if (!row) return { ok: false, error: "This payment was not found." };
  const ctx = await planEditor(row.student_id);
  if (!ctx) return { ok: false, error: "Only Admin and Reception can change fees." };
  if (!(amount > 0) || amount > 10_00_000) return { ok: false, error: "Enter the amount." };
  if (amount < Number(row.paid)) return { ok: false, error: `₹${Number(row.paid)} is already paid for this one. The amount cannot be less.` };
  const month = monthOf(dueDate);
  if (month !== row.month) {
    const { data: clash } = await db.from("fees_ledger").select("id").eq("student_id", row.student_id).eq("month", month).neq("id", row.id).maybeSingle();
    if (clash) return { ok: false, error: "There is already a payment in that month. Change that one instead." };
    const { count } = await db.from("invoices").select("id", { count: "exact", head: true }).eq("student_id", row.student_id).eq("month", row.month);
    if (count) return { ok: false, error: "Bills are already made for this payment, so it must stay in its month. You can change the day." };
  }
  const next = { due_date: dueDate, month, amount, label: label.trim().slice(0, 60) || row.label };
  const { error } = await db.from("fees_ledger").update(next).eq("id", row.id);
  if (error) return { ok: false, error: "Could not save. Please try again." };
  await logActivity(ctx.viewer, "fee.edit", { type: "student", id: row.student_id }, {
    student: ctx.student.name,
    before: { due_date: row.due_date, amount: Number(row.amount), label: row.label },
    after: next,
  });
  revalidatePath(`/fees/${row.student_id}`);
  return { ok: true };
}

/** Add a payment to the plan (one per month). */
export async function addFeeRow(studentId: string, dueDate: string, amount: number, label: string): Promise<PlanResult> {
  const ctx = await planEditor(studentId);
  if (!ctx) return { ok: false, error: "Only Admin and Reception can change fees." };
  if (!isDate(dueDate)) return { ok: false, error: "Choose a date." };
  if (!(amount > 0) || amount > 10_00_000) return { ok: false, error: "Enter the amount." };
  const db = adminClient();
  const month = monthOf(dueDate);
  const { data: clash } = await db.from("fees_ledger").select("id").eq("student_id", studentId).eq("month", month).maybeSingle();
  if (clash) return { ok: false, error: "There is already a payment in that month. Change that one instead." };
  const row = { student_id: studentId, month, due_date: dueDate, amount, label: label.trim().slice(0, 60) || null };
  const { error } = await db.from("fees_ledger").insert(row);
  if (error) return { ok: false, error: "Could not save. Please try again." };
  await logActivity(ctx.viewer, "fee.edit", { type: "student", id: studentId }, { student: ctx.student.name, added: row });
  revalidatePath(`/fees/${studentId}`);
  return { ok: true };
}

/** Remove a payment that has nothing paid and no bill. */
export async function deleteFeeRow(rowId: string): Promise<PlanResult> {
  const db = adminClient();
  if (!UUID.test(rowId)) return { ok: false, error: "Not found." };
  const { data: row } = await db.from("fees_ledger").select("*").eq("id", rowId).maybeSingle();
  if (!row) return { ok: false, error: "This payment was not found." };
  const ctx = await planEditor(row.student_id);
  if (!ctx) return { ok: false, error: "Only Admin and Reception can change fees." };
  const { count } = await db.from("invoices").select("id", { count: "exact", head: true }).eq("student_id", row.student_id).eq("month", row.month);
  if (Number(row.paid) > 0 || count) return { ok: false, error: "Money or bills are recorded for this payment, so it cannot be removed." };
  await db.from("fees_ledger").delete().eq("id", row.id);
  await logActivity(ctx.viewer, "fee.edit", { type: "student", id: row.student_id }, {
    student: ctx.student.name,
    removed: { month: row.month, due_date: row.due_date, amount: Number(row.amount), label: row.label },
  });
  revalidatePath(`/fees/${row.student_id}`);
  return { ok: true };
}

/**
 * Change the plan type, and for monthly plans the fee and due day. The new
 * due day (and fee, where nothing is paid yet) applies from this month on;
 * earlier months keep what they had.
 */
export async function updatePlan(studentId: string, plan: string, monthlyFee: number, dueDay: number): Promise<PlanResult> {
  const ctx = await planEditor(studentId);
  if (!ctx) return { ok: false, error: "Only Admin and Reception can change fees." };
  if (!["monthly", "one_time", "installments", "manual"].includes(plan)) return { ok: false, error: "Choose a plan." };
  if (plan === "monthly" && (!(monthlyFee > 0) || monthlyFee > 1_00_000)) return { ok: false, error: "Enter the monthly fee." };
  if (plan === "monthly" && !(dueDay >= 1 && dueDay <= 28)) return { ok: false, error: "Choose a due day from 1 to 28." };
  const db = adminClient();
  const before = { fee_plan: ctx.student.fee_plan, monthly_fee: Number(ctx.student.monthly_fee), fee_due_day: ctx.student.fee_due_day };
  const after =
    plan === "monthly"
      ? { fee_plan: plan, monthly_fee: monthlyFee, fee_due_day: Math.round(dueDay) }
      : { fee_plan: plan, monthly_fee: 0, fee_due_day: ctx.student.fee_due_day ?? 5 };
  const { error } = await db.from("students").update(after).eq("id", studentId);
  if (error) return { ok: false, error: "Could not save. Has the fee plans update been run in Supabase?" };
  if (plan === "monthly") {
    const current = monthOf(todayIst());
    const { data: rows } = await db.from("fees_ledger").select("*").eq("student_id", studentId).gte("month", current);
    for (const r of (rows ?? []) as { id: string; month: string; paid: number; amount: number }[]) {
      const change: Record<string, unknown> = { due_date: `${r.month.slice(0, 8)}${String(Math.round(dueDay)).padStart(2, "0")}` };
      if (Number(r.paid) === 0) change.amount = monthlyFee;
      await db.from("fees_ledger").update(change).eq("id", r.id);
    }
  }
  await logActivity(ctx.viewer, "fee.edit", { type: "student", id: studentId }, { student: ctx.student.name, before, after });
  revalidatePath(`/fees/${studentId}`);
  return { ok: true };
}
