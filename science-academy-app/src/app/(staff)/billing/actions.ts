"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import { can, canSeeBatch, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { notify, parentUserOf } from "@/lib/notify";
import { billPreview, validModes } from "@/lib/billing-calc";
import { getInvoice, monthPayments, normalizeInvoice } from "@/lib/fees-data";
import { buildBillPdf, billFileName } from "@/lib/bill-pdf";
import { escapeHtml, sendEmail } from "@/lib/email";
import { boardName, parseStudentId, sessionYearFor } from "@/lib/ids";
import { dateLabel, monthLabel, rupees, todayIst } from "@/lib/format";
import type { Invoice } from "@/lib/types";
import type { ActionResult } from "../fees/ActionForm";

export type StudentHit = {
  id: string;
  name: string;
  code: string | null;
  board: string;
  cls: number;
  monthlyFee: number;
  earlierId?: string;
};

/** Student search for the bill form: current or earlier ID, or name. */
export async function searchStudentsForBill(q: string): Promise<StudentHit[]> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "bills.create")) return [];
  const text = q.trim().replace(/[%,()*]/g, " ").trim();
  if (text.length < 2) return [];
  const db = adminClient();
  const cols = "id, name, code, board, current_class, monthly_fee, batch_id";
  const found = new Map<string, StudentHit>();
  const add = (rows: Record<string, unknown>[] | null, earlierId?: string) => {
    for (const s of rows ?? []) {
      if (!canSeeBatch(viewer, (s.batch_id as string | null) ?? null)) continue;
      if (!found.has(String(s.id))) {
        found.set(String(s.id), {
          id: String(s.id),
          name: String(s.name),
          code: (s.code as string | null) ?? null,
          board: String(s.board),
          cls: Number(s.current_class),
          monthlyFee: Number(s.monthly_fee ?? 0),
          earlierId,
        });
      }
    }
  };
  const compact = text.replace(/\s+/g, "").toUpperCase();
  if (parseStudentId(compact) || /^(CB|MP)\d/i.test(compact)) {
    const { data } = await db.from("students").select(cols).neq("status", "draft").ilike("code", `${compact}%`).limit(10);
    add(data);
    const { data: hist } = await db.from("student_id_history").select("student_id, code").ilike("code", `${compact}%`).limit(10);
    const histRows = (hist ?? []) as { student_id: string; code: string }[];
    if (histRows.length) {
      const { data: older } = await db.from("students").select(cols).in("id", histRows.map((h) => h.student_id)).neq("status", "draft");
      for (const s of (older ?? []) as Record<string, unknown>[]) {
        const h = histRows.find((x) => x.student_id === s.id);
        add([s], h && h.code !== s.code ? h.code : undefined);
      }
    }
  } else {
    const { data } = await db.from("students").select(cols).eq("status", "active").ilike("name", `%${text}%`).order("name").limit(12);
    add(data);
  }
  return [...found.values()].slice(0, 12);
}

export type MonthInfo = {
  amount: number | null;
  paid: number;
  bills: { id: string; number: string; received: number; paidOn: string; status: string }[];
};

/** Fee and earlier payments of one month, for the live balance on the bill form. */
export async function loadBillMonth(studentId: string, month: string): Promise<MonthInfo | null> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "bills.create")) return null;
  if (!/^[0-9a-f-]{36}$/i.test(studentId) || !/^\d{4}-\d{2}-01$/.test(month)) return null;
  const m = await monthPayments(studentId, month);
  return {
    amount: m.amount,
    paid: m.paid,
    bills: m.invoices.map((i) => ({ id: i.id, number: i.number, received: i.received, paidOn: i.paid_on, status: i.status })),
  };
}

const BillInput = z.object({
  studentId: z.string().uuid(),
  month: z.string().regex(/^\d{4}-\d{2}$/),
  fee: z.coerce.number().positive().max(10_00_000),
  received: z.coerce.number().positive().max(10_00_000),
  paidOn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  reference: z.string().max(100).optional(),
});

export type BillFormState = { error: string } | null;

/** Makes the bill (next number in the series, no gaps) and opens it. */
export async function createBill(_prev: BillFormState, formData: FormData): Promise<BillFormState> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "bills.create")) return { error: "Your login cannot make bills." };
  const parsed = BillInput.safeParse({
    studentId: formData.get("studentId"),
    month: formData.get("month"),
    fee: formData.get("fee"),
    received: formData.get("received"),
    paidOn: formData.get("paidOn"),
    reference: formData.get("reference") ?? undefined,
  });
  if (!parsed.success) return { error: "Please fill the student, month, fee, amount received and date." };
  const modes = formData.getAll("modes").map(String);
  if (!validModes(modes)) return { error: "Tick at least one payment mode: UPI, Bank transfer or Cash." };
  const { studentId, fee, received, paidOn } = parsed.data;
  const reference = parsed.data.reference?.trim() ?? "";
  if ((modes.includes("upi") || modes.includes("bank")) && !reference && !modes.includes("cash")) {
    return { error: "Enter the transaction reference (UTR) for a UPI or bank payment." };
  }
  const today = todayIst();
  if (paidOn > today) return { error: "The payment date cannot be in the future." };
  const month = `${parsed.data.month}-01`;

  const db = adminClient();
  const { data: student } = await db.from("students").select("id, name, status, batch_id").eq("id", studentId).maybeSingle();
  if (!student || student.status === "draft" || !canSeeBatch(viewer, student.batch_id)) return { error: "Student not found." };

  const before = await monthPayments(studentId, month);
  const preview = billPreview(fee, before.paid, received);
  if (preview.error) return { error: preview.error };

  const { data, error } = await db.rpc("create_invoice", {
    p_student: studentId,
    p_month: month,
    p_fee: preview.fee,
    p_received: preview.received,
    p_modes: modes,
    p_reference: reference,
    p_paid_on: paidOn,
    p_series_year: sessionYearFor(new Date(`${paidOn}T06:30:00Z`)),
    p_created_by: viewer.user.id,
  });
  if (error || !data) {
    console.error("create_invoice failed", error);
    return { error: "Could not make the bill. Please try again." };
  }
  const inv = normalizeInvoice((Array.isArray(data) ? data[0] : data) as Invoice);

  if (before.amount !== null && before.amount !== preview.fee) {
    await logActivity(viewer, "fee.edit", { type: "student", id: studentId }, { month, from: before.amount, to: preview.fee });
  }
  await logActivity(viewer, "bill.create", { type: "invoice", id: inv.id }, { number: inv.number, student: inv.student_code, month, received: inv.received, modes });

  const parent = await parentUserOf(studentId);
  if (parent) {
    await notify([
      {
        userId: parent.id,
        kind: "receipt",
        title: `New receipt ${inv.number}`,
        body: `${rupees(inv.received)} received for ${student.name}, ${monthLabel(month)}. Balance ${rupees(inv.balance_after)}.`,
        link: "/parent/fees",
        dedupeKey: `receipt:${inv.id}`,
      },
    ]);
  }
  revalidatePath("/billing");
  revalidatePath("/fees");
  redirect(`/billing/${inv.id}`);
}

/** Only Admin (bills.cancel). The number stays in the list, marked cancelled. */
export async function cancelBill(_prev: ActionResult, formData: FormData): Promise<ActionResult> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "bills.cancel")) return { ok: false, message: "Only Admin can cancel a bill." };
  const id = String(formData.get("id") ?? "");
  const reason = String(formData.get("reason") ?? "").trim();
  if (reason.length < 3) return { ok: false, message: "Write the reason for cancelling." };
  const inv = await getInvoice(id);
  if (!inv) return { ok: false, message: "Bill not found." };
  if (inv.status === "cancelled") return { ok: false, message: "This bill is already cancelled." };
  const { error } = await adminClient().rpc("cancel_invoice", { p_invoice: id, p_reason: reason.slice(0, 500), p_by: viewer.user.id });
  if (error) return { ok: false, message: "Could not cancel the bill." };
  await logActivity(viewer, "bill.cancel", { type: "invoice", id }, { number: inv.number, reason, received: inv.received });
  revalidatePath(`/billing/${id}`);
  revalidatePath("/billing");
  revalidatePath(`/fees/${inv.student_id}`);
  return { ok: true, message: "Bill cancelled." };
}

/** Emails the parent copy PDF to the email on the student's profile. */
export async function emailBill(_prev: ActionResult, formData: FormData): Promise<ActionResult> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "bills.create")) return { ok: false, message: "No access." };
  const inv = await getInvoice(String(formData.get("id") ?? ""));
  if (!inv) return { ok: false, message: "Bill not found." };
  const { data: student } = await adminClient().from("students").select("email, batch_id").eq("id", inv.student_id).maybeSingle();
  if (!student || !canSeeBatch(viewer, student.batch_id)) return { ok: false, message: "Bill not found." };
  if (!student.email) return { ok: false, message: "No email on the student's profile. Add it on the profile first." };
  const pdf = await buildBillPdf(inv, { copies: ["Parent copy"] });
  const sent = await sendEmail({
    to: student.email,
    subject: `Fee receipt ${inv.number} · ${inv.student_name} · Science Academy`,
    html: `<p>Dear Parent,</p><p>Please find attached the fee receipt <b>${escapeHtml(inv.number)}</b> for <b>${escapeHtml(inv.student_name)}</b> (${escapeHtml(inv.student_code)}, Class ${inv.class} ${boardName(inv.board)}), ${monthLabel(inv.month)}.</p><p>Received: <b>${escapeHtml(rupees(inv.received))}</b> on ${dateLabel(inv.paid_on)}. Balance: ${escapeHtml(rupees(inv.balance_after))}.</p><p>Thank you,<br/>Science Academy, Ratlam</p>`,
    attachments: [{ filename: billFileName(inv), content: pdf }],
  });
  if (!sent.ok) return { ok: false, message: sent.error };
  await adminClient().from("invoices").update({ emailed_at: new Date().toISOString() }).eq("id", inv.id);
  await logActivity(viewer, "bill.email", { type: "invoice", id: inv.id }, { number: inv.number, to: student.email });
  revalidatePath(`/billing/${inv.id}`);
  return { ok: true, message: `Emailed to ${student.email}.` };
}

/** Logged when the bill is printed (both copies). */
export async function logBillPrint(id: string): Promise<void> {
  const viewer = await staffForApi();
  if (!viewer || !(can(viewer, "bills.create") || can(viewer, "fees.view"))) return;
  const inv = await getInvoice(id);
  if (inv) await logActivity(viewer, "bill.print", { type: "invoice", id }, { number: inv.number });
}
