"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CalendarClock, Plus, Trash2, Wand2 } from "lucide-react";
import { FEE_PLAN_LABEL, addMonthsToDate, checkSchedule, makeInstallments, scheduleTotal, type FeePlan, type Installment } from "@/lib/fees";

export type FeePlanInitial = {
  fee_plan: FeePlan;
  monthly_fee: number;
  fee_due_day: number;
  fee_schedule: Installment[];
};

const fmt = (n: number) => `₹${new Intl.NumberFormat("en-IN").format(n)}`;

function today(): string {
  const d = new Date(Date.now() + 330 * 60_000);
  return d.toISOString().slice(0, 10);
}

function Err({ msg }: { msg?: string }) {
  return msg ? <p className="mt-1 text-xs font-semibold text-danger">{msg}</p> : null;
}

/**
 * "Fees & payment plan" at registration: Monthly (fee + due day), One time,
 * Installments (total, how many, first date, gap → schedule) or a Manual
 * schedule. The schedule is editable and saved as JSON in fee_schedule.
 * For a registered student it is read only (change it on the Fees page).
 */
export function FeePlanFields({
  initial,
  errors,
  locked,
  studentId,
}: {
  initial: FeePlanInitial | null;
  errors: Record<string, string>;
  locked?: boolean;
  studentId?: string;
}) {
  const [plan, setPlan] = useState<FeePlan>(initial?.fee_plan ?? "monthly");
  const [monthly, setMonthly] = useState(initial && initial.monthly_fee ? String(initial.monthly_fee) : "");
  const [dueDay, setDueDay] = useState(String(initial?.fee_due_day ?? 5));
  const [rows, setRows] = useState<Installment[]>(initial?.fee_schedule ?? []);
  // Installment helper inputs.
  const [total, setTotal] = useState(initial?.fee_schedule?.length ? String(scheduleTotal(initial.fee_schedule)) : "");
  const [count, setCount] = useState("3");
  const [first, setFirst] = useState(today());
  const [gap, setGap] = useState("1");

  const problem = plan === "monthly" ? null : checkSchedule(rows);
  const json = useMemo(() => JSON.stringify(rows), [rows]);

  if (locked) {
    return (
      <section className="rounded-card bg-card p-4 shadow-card">
        <h2 className="text-[15px] font-bold text-navy">Fees &amp; payment plan</h2>
        <input type="hidden" name="fee_plan" value={initial?.fee_plan ?? "monthly"} />
        <input type="hidden" name="monthly_fee" value={String(initial?.monthly_fee ?? 0)} />
        <input type="hidden" name="fee_due_day" value={String(initial?.fee_due_day ?? 5)} />
        <p className="mt-1 text-sm">
          {FEE_PLAN_LABEL[initial?.fee_plan ?? "monthly"]}
          {(initial?.fee_plan ?? "monthly") === "monthly"
            ? ` · ${fmt(initial?.monthly_fee ?? 0)} a month, due on day ${initial?.fee_due_day ?? 5}`
            : ` · ${initial?.fee_schedule.length ?? 0} payments, ${fmt(scheduleTotal(initial?.fee_schedule ?? []))}`}
        </p>
        {studentId && (
          <Link href={`/fees/${studentId}`} className="mt-2 inline-block text-sm font-bold text-primary">
            Change the plan, amounts or due dates on the Fees page →
          </Link>
        )}
      </section>
    );
  }

  const setOneTime = (date: string, amount: string) =>
    setRows([{ due_date: date, amount: Number(amount) || 0, label: "Full fee (one time)" }]);

  return (
    <section className="rounded-card bg-card p-4 shadow-card">
      <h2 className="text-[15px] font-bold text-navy">Fees &amp; payment plan</h2>
      <p className="mb-3 text-xs text-muted">How the parent will pay. The app makes the payment schedule from this and reminds on each due date.</p>
      <input type="hidden" name="fee_plan" value={plan} />
      <input type="hidden" name="fee_schedule" value={plan === "monthly" ? "[]" : json} />

      <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Payment plan">
        {(Object.keys(FEE_PLAN_LABEL) as FeePlan[]).map((p) => (
          <button
            key={p}
            type="button"
            role="radio"
            aria-checked={plan === p}
            onClick={() => {
              setPlan(p);
              if (p === "one_time") setRows(rows.length ? [{ ...rows[0], amount: Number(total) || rows[0].amount, label: "Full fee (one time)" }] : []);
            }}
            className={`rounded-field border px-3 py-2 text-left text-[13px] font-bold ${
              plan === p ? "border-primary bg-primary-soft text-primary" : "border-line bg-card text-fg hover:border-primary"
            }`}
          >
            {p === "one_time" ? "One time" : p === "manual" ? "Manual" : FEE_PLAN_LABEL[p]}
          </button>
        ))}
      </div>

      {plan === "monthly" && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="monthly_fee">Monthly fee (₹)</label>
            <input id="monthly_fee" name="monthly_fee" className="field" inputMode="decimal" placeholder="2500" value={monthly} onChange={(e) => setMonthly(e.target.value)} />
            <Err msg={errors.monthly_fee} />
          </div>
          <div>
            <label className="label" htmlFor="fee_due_day">Due on (day of every month)</label>
            <select id="fee_due_day" name="fee_due_day" className="field" value={dueDay} onChange={(e) => setDueDay(e.target.value)}>
              {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                <option key={d} value={d}>
                  {d}
                  {d === 1 ? "st" : d === 2 ? "nd" : d === 3 ? "rd" : d === 21 ? "st" : d === 22 ? "nd" : d === 23 ? "rd" : "th"} of every month
                </option>
              ))}
            </select>
            <Err msg={errors.fee_due_day} />
          </div>
        </div>
      )}

      {plan !== "monthly" && <input type="hidden" name="monthly_fee" value="0" />}

      {plan === "one_time" && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="ot_amount">Total fee (₹)</label>
            <input
              id="ot_amount"
              className="field"
              inputMode="decimal"
              placeholder="30000"
              value={rows[0]?.amount ? String(rows[0].amount) : total}
              onChange={(e) => {
                setTotal(e.target.value);
                setOneTime(rows[0]?.due_date ?? today(), e.target.value);
              }}
            />
          </div>
          <div>
            <label className="label" htmlFor="ot_date">Pay by (date)</label>
            <input id="ot_date" type="date" className="field" value={rows[0]?.due_date ?? ""} onChange={(e) => setOneTime(e.target.value, String(rows[0]?.amount ?? total))} />
          </div>
        </div>
      )}

      {plan === "installments" && (
        <div className="rounded-field border border-dashed border-line p-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <label className="label" htmlFor="in_total">Total fee (₹)</label>
              <input id="in_total" className="field" inputMode="decimal" placeholder="30000" value={total} onChange={(e) => setTotal(e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="in_count">How many</label>
              <select id="in_count" className="field" value={count} onChange={(e) => setCount(e.target.value)}>
                {Array.from({ length: 11 }, (_, i) => i + 2).map((n) => (
                  <option key={n} value={n}>
                    {n} installments
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="in_first">First payment on</label>
              <input id="in_first" type="date" className="field" value={first} onChange={(e) => setFirst(e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="in_gap">Then every</label>
              <select id="in_gap" className="field" value={gap} onChange={(e) => setGap(e.target.value)}>
                <option value="1">1 month</option>
                <option value="2">2 months</option>
                <option value="3">3 months</option>
                <option value="4">4 months</option>
                <option value="6">6 months</option>
              </select>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-soft mt-3"
            disabled={!(Number(total) > 0) || !first}
            onClick={() => setRows(makeInstallments(Number(total), Number(count), first, Number(gap)))}
          >
            <Wand2 size={16} /> Make the schedule
          </button>
          <p className="mt-1.5 text-xs text-muted">Splits the total equally. You can change any date or amount below.</p>
        </div>
      )}

      {(plan === "installments" || plan === "manual") && (
        <div className="mt-3">
          {rows.length > 0 && (
            <div className="space-y-2">
              {rows.map((r, i) => (
                <div key={i} className="grid grid-cols-[1fr_1fr_auto] items-center gap-2 sm:grid-cols-[1.2fr_1fr_1fr_auto]">
                  <input
                    className="field hidden py-2 text-[14px] sm:block"
                    value={r.label}
                    aria-label={`Payment ${i + 1} name`}
                    onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))}
                  />
                  <input
                    type="date"
                    className="field py-2 text-[14px]"
                    value={r.due_date}
                    aria-label={`Payment ${i + 1} date`}
                    onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, due_date: e.target.value } : x)))}
                  />
                  <input
                    className="field py-2 text-[14px]"
                    inputMode="decimal"
                    value={r.amount ? String(r.amount) : ""}
                    placeholder="Amount"
                    aria-label={`Payment ${i + 1} amount`}
                    onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, amount: Number(e.target.value) || 0 } : x)))}
                  />
                  <button type="button" onClick={() => setRows(rows.filter((_, j) => j !== i))} className="grid h-9 w-9 place-items-center rounded-full text-muted hover:bg-danger-soft hover:text-danger" aria-label={`Remove payment ${i + 1}`}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
          <button
            type="button"
            className="btn btn-ghost mt-2 py-1.5 text-[13px]"
            onClick={() => {
              const last = rows[rows.length - 1]?.due_date;
              setRows([...rows, { due_date: last ? addMonthsToDate(last, 1) : today(), amount: 0, label: `Payment ${rows.length + 1}` }]);
            }}
          >
            <Plus size={15} /> Add a payment
          </button>
        </div>
      )}

      {plan !== "monthly" && rows.length > 0 && (
        <div className="mt-3 rounded-field bg-field px-3 py-2.5 text-[13px]">
          <p className="flex items-center gap-1.5 font-bold text-navy">
            <CalendarClock size={15} /> {rows.length} payment{rows.length === 1 ? "" : "s"} · total {fmt(scheduleTotal(rows))}
          </p>
          <ul className="mt-1 space-y-0.5 text-muted">
            {[...rows]
              .sort((a, b) => a.due_date.localeCompare(b.due_date))
              .map((r, i) => (
                <li key={i}>
                  {r.label || `Payment ${i + 1}`}: <span className="font-semibold text-fg">{fmt(r.amount)}</span> by{" "}
                  {r.due_date ? new Date(`${r.due_date}T00:00:00Z`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "—"}
                </li>
              ))}
          </ul>
        </div>
      )}
      <Err msg={errors.fee_schedule ?? (rows.length > 0 ? (problem ?? undefined) : undefined)} />
    </section>
  );
}
