// Reads the "Fees & payment plan" part of the registration form (pure, tested).

import { dueDate, scheduleTotal, type FeePlan, type Installment } from "./fees";
import { translator, type DictKey, type Params, type TFn } from "./i18n";
import { monthStart } from "./format";

export type ParsedFeePlan = {
  fee_plan: FeePlan;
  monthly_fee: number;
  fee_due_day: number;
  total_fee: number | null;
  /** Monthly: empty (rows are made each month). Others: every payment. */
  fee_schedule: Installment[];
};

const PLANS: FeePlan[] = ["monthly", "one_time", "installments", "manual"];

/**
 * fee_plan, monthly_fee, fee_due_day (monthly) and fee_schedule (JSON of
 * {due_date, amount, label} for the other plans). `strict` is for Register;
 * a draft keeps whatever was filled in.
 */
export function parseFeePlan(
  form: FormData,
  strict: boolean,
  t: TFn = translator("en"),
): { ok: true; data: ParsedFeePlan } | { ok: false; errors: Record<string, string> } {
  const get = (k: string) => String(form.get(k) ?? "").trim();
  const plan = (PLANS as string[]).includes(get("fee_plan")) ? (get("fee_plan") as FeePlan) : "monthly";
  const errors: Record<string, string> = {};

  if (plan === "monthly") {
    const fee = Number(get("monthly_fee") || "0");
    const day = Math.round(Number(get("fee_due_day") || "5"));
    if (!Number.isFinite(fee) || fee < 0 || fee > 1_00_000) errors.monthly_fee = t("students.err.monthlyFee");
    else if (strict && fee <= 0) errors.monthly_fee = t("students.err.monthlyFee");
    if (!(day >= 1 && day <= 28)) errors.fee_due_day = t("students.err.dueDay");
    if (Object.keys(errors).length && strict) return { ok: false, errors };
    return {
      ok: true,
      data: { fee_plan: "monthly", monthly_fee: Number.isFinite(fee) && fee > 0 ? fee : 0, fee_due_day: day >= 1 && day <= 28 ? day : 5, total_fee: null, fee_schedule: [] },
    };
  }

  let rows: Installment[] = [];
  try {
    const raw = JSON.parse(get("fee_schedule") || "[]") as unknown;
    if (Array.isArray(raw)) {
      rows = raw
        .map((r, i) => ({
          due_date: String((r as Installment)?.due_date ?? "").slice(0, 10),
          amount: Math.round(Number((r as Installment)?.amount) * 100) / 100,
          label: String((r as Installment)?.label ?? "").trim().slice(0, 60) || `Payment ${i + 1}`,
        }))
        .sort((a, b) => a.due_date.localeCompare(b.due_date));
    }
  } catch {
    rows = [];
  }
  if (plan === "one_time" && rows.length) rows = [{ ...rows[0], label: "Full fee (one time)" }];
  const issue = scheduleProblem(rows);
  const problem = issue ? t(issue.key, issue.params) : null;
  if (problem) errors.fee_schedule = problem;
  if (Object.keys(errors).length && strict) return { ok: false, errors };
  return {
    ok: true,
    data: { fee_plan: plan, monthly_fee: 0, fee_due_day: 5, total_fee: rows.length ? scheduleTotal(rows) : null, fee_schedule: problem ? rows.filter((r) => r.due_date && r.amount > 0) : rows },
  };
}

/**
 * What is wrong with a payment schedule, as a dictionary key (same rules as
 * checkSchedule in fees.ts: dates, amounts, one payment per month). Null when fine.
 */
export function scheduleProblem(rows: Installment[]): { key: DictKey; params?: Params } | null {
  if (!rows.length) return { key: "students.err.schedEmpty" };
  const months = new Set<string>();
  for (const [i, r] of rows.entries()) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.due_date)) return { key: "students.err.schedDate", params: { n: i + 1 } };
    if (!(Number(r.amount) > 0)) return { key: "students.err.schedAmount", params: { n: i + 1 } };
    const m = r.due_date.slice(0, 7);
    if (months.has(m)) return { key: "students.err.schedSameMonth" };
    months.add(m);
  }
  return null;
}

export type NewLedgerRow = {
  student_id: string;
  month: string;
  amount: number;
  due_date: string;
  label: string | null;
  installment_no: number | null;
};

/** The fee rows a registration makes: monthly → this month's row; others → one row per payment. */
export function ledgerRowsFor(studentId: string, plan: ParsedFeePlan, today: string): NewLedgerRow[] {
  if (plan.fee_plan === "monthly") {
    if (plan.monthly_fee <= 0) return [];
    const m = monthStart(today);
    return [{ student_id: studentId, month: m, amount: plan.monthly_fee, due_date: dueDate(m, plan.fee_due_day), label: null, installment_no: null }];
  }
  return plan.fee_schedule.map((r, i) => ({
    student_id: studentId,
    month: monthStart(r.due_date),
    amount: r.amount,
    due_date: r.due_date,
    label: r.label,
    installment_no: i + 1,
  }));
}
