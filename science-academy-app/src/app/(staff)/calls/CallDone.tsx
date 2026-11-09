"use client";

import { useActionState, useEffect, useState } from "react";
import { CheckCircle2, LoaderCircle, X } from "lucide-react";
import { CALL_OUTCOME_LABEL } from "@/lib/fees";
import { useT } from "@/components/I18nProvider";
import type { ActionResult } from "../fees/ActionForm";
import { logCall } from "./actions";

type Option = { id: string; label: string };

/** "Call done" button and the outcome sheet. */
export function CallDone({ studentId, studentName, numbers, attempt, today }: { studentId: string; studentName: string; numbers: Option[]; attempt: number; today: string }) {
  const tr = useT();
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState<string>("");
  const [state, run, pending] = useActionState<ActionResult, FormData>(logCall, null);

  useEffect(() => {
    if (state?.ok) {
      const t = setTimeout(() => {
        setOpen(false);
        setOutcome("");
      }, 900);
      return () => clearTimeout(t);
    }
  }, [state]);

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="btn btn-green px-3 py-1.5 text-[13px]">
        <CheckCircle2 size={15} /> {tr("fees.cd.callDone")}
      </button>
      {open && (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 lg:items-center" onClick={() => !pending && setOpen(false)}>
          <form
            action={run}
            onClick={(e) => e.stopPropagation()}
            className="safe-bottom w-full max-w-md rounded-t-card bg-card p-5 shadow-sheet lg:rounded-card"
          >
            <input type="hidden" name="studentId" value={studentId} />
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <p className="text-lg font-extrabold text-navy">{tr("fees.cd.howWent")}</p>
                <p className="text-sm text-muted">
                  {studentName} · {tr("fees.cd.attempt", { n: attempt })}
                </p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="grid h-8 w-8 place-items-center rounded-full hover:bg-field" aria-label={tr("core.close")}>
                <X size={18} />
              </button>
            </div>
            {numbers.length > 1 ? (
              <label className="mb-3 block">
                <span className="label">{tr("fees.cd.numberCalled")}</span>
                <select name="guardianId" className="field">
                  {numbers.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <input type="hidden" name="guardianId" value={numbers[0]?.id ?? ""} />
            )}
            <div className="grid gap-2">
              {Object.keys(CALL_OUTCOME_LABEL).map((key) => (
                <label key={key} className={`flex cursor-pointer items-center gap-3 rounded-field border px-3 py-2.5 text-[15px] font-semibold ${outcome === key ? "border-primary bg-primary-soft text-primary" : "border-line"}`}>
                  <input type="radio" name="outcome" value={key} checked={outcome === key} onChange={() => setOutcome(key)} className="accent-[var(--color-primary)]" />
                  {tr(`fees.call.${key as keyof typeof CALL_OUTCOME_LABEL}`)}
                </label>
              ))}
            </div>
            {outcome === "promised_date" && (
              <label className="mt-3 block">
                <span className="label">{tr("fees.cd.promisedDate")}</span>
                <input type="date" name="followUpDate" min={today} required className="field" />
              </label>
            )}
            <label className="mt-3 block">
              <span className="label">{tr("fees.cd.note")}</span>
              <textarea name="note" rows={2} className="field" placeholder={tr("fees.cd.notePlaceholder")} />
            </label>
            {state && <p className={`mt-2 text-sm font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
            <button className="btn btn-primary mt-4 w-full py-3" disabled={pending || !outcome}>
              {pending && <LoaderCircle size={16} className="animate-spin" />} {tr("fees.cd.saveCall")}
            </button>
          </form>
        </div>
      )}
    </>
  );
}
