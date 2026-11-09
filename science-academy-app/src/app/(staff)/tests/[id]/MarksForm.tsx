"use client";

import { useActionState } from "react";
import { LoaderCircle } from "lucide-react";
import { saveMarks, type MarksState } from "./actions";
import { useT } from "@/components/I18nProvider";

export type MarksRow = { id: string; name: string; code: string | null; batch: string; score: number | null; absent: boolean };

export function MarksForm({ testId, max, rows, readOnly }: { testId: string; max: number | null; rows: MarksRow[]; readOnly: boolean }) {
  const t = useT();
  const [state, action, pending] = useActionState<MarksState, FormData>(saveMarks, null);
  return (
    <form action={action} className="space-y-3">
      <input type="hidden" name="testId" value={testId} />
      <ul className="divide-y divide-line overflow-hidden rounded-card bg-card shadow-card">
        {rows.map((r, i) => (
          <li key={r.id} className="flex items-center gap-3 px-3 py-2.5 sm:px-4">
            <span className="w-6 shrink-0 text-right text-xs font-bold text-faint">{i + 1}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[15px] font-semibold">{r.name}</p>
              <p className="truncate text-[11.5px] text-muted">
                {r.code}
                {r.batch ? ` · ${r.batch}` : ""}
              </p>
            </div>
            <input
              name={`score-${r.id}`}
              type="number"
              inputMode="decimal"
              step="0.5"
              min={0}
              max={max ?? undefined}
              defaultValue={r.score ?? ""}
              disabled={readOnly}
              aria-label={t("academics.marks.of", { name: r.name })}
              className="field w-20 py-2 text-center font-bold"
            />
            {max !== null && <span className="hidden w-10 text-xs text-muted sm:inline">/ {max}</span>}
            <label className="flex shrink-0 items-center gap-1.5 text-xs font-semibold text-muted">
              <input type="checkbox" name={`absent-${r.id}`} defaultChecked={r.absent} disabled={readOnly} className="h-4 w-4 accent-[var(--color-danger)]" />
              {t("academics.absent")}
            </label>
          </li>
        ))}
      </ul>
      {state && <p className={`text-sm font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
      {!readOnly && (
        <div className="sticky bottom-20 lg:bottom-4">
          <button className="btn btn-green w-full py-3 shadow-card" disabled={pending}>
            {pending && <LoaderCircle size={18} className="animate-spin" />}
            {t("academics.marks.save")}
          </button>
        </div>
      )}
    </form>
  );
}
