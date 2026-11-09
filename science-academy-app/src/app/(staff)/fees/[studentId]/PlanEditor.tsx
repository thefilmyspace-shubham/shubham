"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, Check, LoaderCircle, Pencil, Plus, Trash2, X } from "lucide-react";
import { FEE_PLAN_LABEL, type FeePlan, type FeeStatus } from "@/lib/fees";
import { useT } from "@/components/I18nProvider";
import { addFeeRow, deleteFeeRow, updateFeeRow, updatePlan } from "../actions";
import { FeeStatusChip } from "../StatusChip";

export type PlanRow = {
  id: string;
  month: string;
  label: string | null;
  due: string;
  amount: number;
  paid: number;
  balance: number;
  status: FeeStatus;
};

const fmt = (n: number) => `₹${new Intl.NumberFormat("en-IN").format(n)}`;
const nice = (d: string) => new Date(`${d}T00:00:00Z`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const monthName = (m: string) => new Date(`${m}T00:00:00Z`).toLocaleDateString("en-IN", { month: "long", year: "numeric", timeZone: "UTC" });

/**
 * The student's payment plan: plan type (monthly fee and due day), and every
 * payment with its due date and amount. Editable by Admin and Reception.
 */
export function PlanEditor({
  studentId,
  plan,
  monthlyFee,
  dueDay,
  rows,
  canEdit,
}: {
  studentId: string;
  plan: FeePlan;
  monthlyFee: number;
  dueDay: number;
  rows: PlanRow[];
  canEdit: boolean;
}) {
  const router = useRouter();
  const t = useT();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState({ due: "", amount: "", label: "" });
  const [planOpen, setPlanOpen] = useState(false);
  const [p, setP] = useState({ plan, fee: String(monthlyFee || ""), day: String(dueDay) });

  const run = (fn: () => Promise<{ ok: true } | { ok: false; error: string }>, after?: () => void) =>
    start(async () => {
      setError(null);
      const res = await fn();
      if (!res.ok) setError(res.error);
      else {
        after?.();
        router.refresh();
      }
    });

  const total = rows.reduce((s, r) => s + r.amount, 0);
  return (
    <div className="rounded-card bg-card shadow-card">
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
        <CalendarClock size={18} className="text-primary" />
        <div className="min-w-0 flex-1">
          <p className="font-bold text-navy">{t(`fees.plan.${plan}`)}</p>
          <p className="text-xs text-muted">
            {plan === "monthly" ? t("fees.pe.monthlySummary", { amount: fmt(monthlyFee), day: dueDay }) : t("fees.pe.planSummary", { n: rows.length, total: fmt(total) })}
          </p>
        </div>
        {canEdit && (
          <button type="button" className="btn btn-ghost py-1.5 text-[13px]" onClick={() => setPlanOpen(!planOpen)}>
            <Pencil size={14} /> {t("fees.pe.changePlan")}
          </button>
        )}
      </div>

      {planOpen && canEdit && (
        <div className="grid grid-cols-1 gap-3 border-b border-line bg-field/60 px-4 py-3 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
          <div>
            <label className="label">{t("fees.pe.plan")}</label>
            <select className="field" value={p.plan} onChange={(e) => setP({ ...p, plan: e.target.value as FeePlan })}>
              {(Object.keys(FEE_PLAN_LABEL) as FeePlan[]).map((k) => (
                <option key={k} value={k}>
                  {t(`fees.plan.${k}`)}
                </option>
              ))}
            </select>
          </div>
          {p.plan === "monthly" ? (
            <>
              <div>
                <label className="label">{t("fees.pe.monthlyFeeRs")}</label>
                <input className="field" inputMode="decimal" value={p.fee} onChange={(e) => setP({ ...p, fee: e.target.value })} />
              </div>
              <div>
                <label className="label">{t("fees.pe.dueOnDay")}</label>
                <select className="field" value={p.day} onChange={(e) => setP({ ...p, day: e.target.value })}>
                  {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                    <option key={d} value={d}>
                      {t("fees.pe.dayOfEveryMonth", { d })}
                    </option>
                  ))}
                </select>
              </div>
            </>
          ) : (
            <p className="text-xs text-muted sm:col-span-2">{t("fees.pe.addChangeHint")}</p>
          )}
          <button
            type="button"
            className="btn btn-primary"
            disabled={pending}
            onClick={() => run(() => updatePlan(studentId, p.plan, Number(p.fee), Number(p.day)), () => setPlanOpen(false))}
          >
            {pending ? <LoaderCircle size={15} className="animate-spin" /> : <Check size={15} />} {t("core.save")}
          </button>
          {p.plan === "monthly" && <p className="text-xs text-muted sm:col-span-4">{t("fees.pe.appliesFromNow")}</p>}
        </div>
      )}

      {error && <p className="px-4 pt-3 text-[13px] font-semibold text-danger">{error}</p>}

      {rows.length === 0 ? (
        <p className="px-4 py-5 text-sm text-muted">{t("fees.pe.noPayments")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((r) =>
            editing === r.id ? (
              <li key={r.id} className="grid grid-cols-1 gap-2 bg-primary-soft/40 px-4 py-3 sm:grid-cols-[1.2fr_1fr_1fr_auto] sm:items-end">
                <div>
                  <label className="label">{t("fees.pe.name")}</label>
                  <input className="field py-2" value={draft.label} placeholder={monthName(r.month)} onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
                </div>
                <div>
                  <label className="label">{t("fees.pe.dueDate")}</label>
                  <input type="date" className="field py-2" value={draft.due} onChange={(e) => setDraft({ ...draft, due: e.target.value })} />
                </div>
                <div>
                  <label className="label">{t("fees.pe.amountRs")}</label>
                  <input className="field py-2" inputMode="decimal" value={draft.amount} onChange={(e) => setDraft({ ...draft, amount: e.target.value })} />
                </div>
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    className="btn btn-primary py-2"
                    disabled={pending}
                    onClick={() => run(() => updateFeeRow(r.id, draft.due, Number(draft.amount), draft.label), () => setEditing(null))}
                  >
                    {pending ? <LoaderCircle size={15} className="animate-spin" /> : <Check size={15} />} {t("core.save")}
                  </button>
                  <button type="button" className="btn btn-ghost py-2" onClick={() => setEditing(null)} aria-label={t("core.cancel")}>
                    <X size={15} />
                  </button>
                </div>
              </li>
            ) : (
              <li key={r.id} className="flex items-center gap-3 px-4 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-semibold">{r.label ?? monthName(r.month)}</p>
                  <p className="text-xs text-muted">
                    {t("fees.pe.due")} <span className="font-semibold text-fg">{nice(r.due)}</span> · {t("fees.pe.paidAmount", { amount: fmt(r.paid) })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold">{fmt(r.amount)}</p>
                  <FeeStatusChip status={r.status} />
                </div>
                {canEdit && (
                  <div className="flex shrink-0 gap-0.5">
                    <button
                      type="button"
                      className="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-field hover:text-primary"
                      aria-label={t("fees.pe.changeDueAmount")}
                      title={t("fees.pe.changeDueAmount")}
                      onClick={() => {
                        setEditing(r.id);
                        setDraft({ due: r.due, amount: String(r.amount), label: r.label ?? "" });
                        setError(null);
                      }}
                    >
                      <Pencil size={15} />
                    </button>
                    {r.paid === 0 && (
                      <button
                        type="button"
                        className="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-danger-soft hover:text-danger"
                        aria-label={t("fees.pe.removePayment")}
                        title={t("fees.pe.removePayment")}
                        disabled={pending}
                        onClick={() => {
                          if (window.confirm(t("fees.pe.removeConfirm"))) run(() => deleteFeeRow(r.id));
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                )}
              </li>
            ),
          )}
        </ul>
      )}

      {canEdit && (
        <div className="border-t border-line px-4 py-3">
          {editing === "new" ? (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1.2fr_1fr_1fr_auto] sm:items-end">
              <div>
                <label className="label">{t("fees.pe.name")}</label>
                <input className="field py-2" value={draft.label} placeholder={t("fees.pe.namePlaceholder")} onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
              </div>
              <div>
                <label className="label">{t("fees.pe.dueDate")}</label>
                <input type="date" className="field py-2" value={draft.due} onChange={(e) => setDraft({ ...draft, due: e.target.value })} />
              </div>
              <div>
                <label className="label">{t("fees.pe.amountRs")}</label>
                <input className="field py-2" inputMode="decimal" value={draft.amount} onChange={(e) => setDraft({ ...draft, amount: e.target.value })} />
              </div>
              <div className="flex gap-1.5">
                <button
                  type="button"
                  className="btn btn-primary py-2"
                  disabled={pending}
                  onClick={() => run(() => addFeeRow(studentId, draft.due, Number(draft.amount), draft.label), () => setEditing(null))}
                >
                  {pending ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />} {t("fees.pe.add")}
                </button>
                <button type="button" className="btn btn-ghost py-2" onClick={() => setEditing(null)} aria-label={t("core.cancel")}>
                  <X size={15} />
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="btn btn-soft py-1.5 text-[13px]"
              onClick={() => {
                setEditing("new");
                setDraft({ due: "", amount: "", label: "" });
                setError(null);
              }}
            >
              <Plus size={15} /> {t("fees.pe.addPayment")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
