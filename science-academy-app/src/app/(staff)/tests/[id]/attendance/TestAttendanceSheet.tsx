"use client";

import { useActionState, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCheck, CheckCircle2, LoaderCircle } from "lucide-react";
import { saveTestAttendance, type TestAttState } from "./actions";
import { useT } from "@/components/I18nProvider";

type Status = "P" | "A";
export type TestAttRow = { id: string; name: string; code: string | null; batch: string; status: Status | null };

export function TestAttendanceSheet({ testId, rows, done, marksHref }: { testId: string; rows: TestAttRow[]; done: boolean; marksHref: string | null }) {
  const t = useT();
  const [marks, setMarks] = useState<Record<string, Status | null>>(() => Object.fromEntries(rows.map((r) => [r.id, r.status])));
  const [state, action, pending] = useActionState<TestAttState, FormData>(saveTestAttendance, null);
  const [doneClicked, setDoneClicked] = useState(false);
  const counts = useMemo(() => {
    const c = { P: 0, A: 0, left: 0 };
    for (const r of rows) {
      const s = marks[r.id];
      if (s) c[s]++;
      else c.left++;
    }
    return c;
  }, [marks, rows]);
  const entries = Object.fromEntries(rows.filter((r) => marks[r.id]).map((r) => [r.id, marks[r.id]]));
  const isDone = done || Boolean(state?.ok && state.done);

  return (
    <form action={action} className="space-y-3">
      <input type="hidden" name="testId" value={testId} />
      <input type="hidden" name="entries" value={JSON.stringify(entries)} />

      <div className="sticky top-14 z-[5] -mx-4 grid grid-cols-3 gap-2 bg-bg/95 px-4 py-2 backdrop-blur lg:static lg:mx-0 lg:px-0">
        <Count label={t("academics.att.present")} value={counts.P} className="text-green" />
        <Count label={t("academics.absent")} value={counts.A} className="text-danger" />
        <Count label={t("academics.att.notMarked")} value={counts.left} className="text-muted" />
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          className="btn btn-soft py-1.5 text-[13px]"
          onClick={() =>
            setMarks((m) => {
              const next = { ...m };
              for (const r of rows) if (!next[r.id]) next[r.id] = "P";
              return next;
            })
          }
        >
          <CheckCheck size={15} /> {t("academics.att.allPresent")}
        </button>
      </div>

      <ul className="divide-y divide-line overflow-hidden rounded-card bg-card shadow-card">
        {rows.map((r, i) => {
          const current = marks[r.id];
          return (
            <li key={r.id} className="flex items-center gap-3 px-3 py-2.5 sm:px-4">
              <span className="w-6 shrink-0 text-right text-xs font-bold text-faint">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-semibold">{r.name}</p>
                <p className="truncate text-[11.5px] text-muted">
                  {r.code}
                  {r.batch ? ` · ${r.batch}` : ""}
                </p>
              </div>
              <div className="flex shrink-0 gap-1.5">
                {(["P", "A"] as Status[]).map((s) => (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={current === s}
                    aria-label={`${t(s === "P" ? "academics.att.present" : "academics.absent")}: ${r.name}`}
                    onClick={() => setMarks((m) => ({ ...m, [r.id]: s }))}
                    className={`h-11 w-11 rounded-full border-2 text-[15px] font-extrabold transition-colors ${
                      current === s ? (s === "P" ? "border-green bg-green text-white" : "border-danger bg-danger text-white") : "border-line bg-card text-muted"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </li>
          );
        })}
      </ul>

      {state && <p className={`text-sm font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
      {state?.ok && marksHref && (
        <Link href={marksHref} className="btn btn-soft w-full">
          {t("academics.duty.enterMarks")}
        </Link>
      )}

      <div className="sticky bottom-20 flex flex-col gap-2 sm:flex-row lg:bottom-4">
        <button className="btn btn-ghost flex-1 py-3 shadow-card" disabled={pending} onClick={() => setDoneClicked(false)}>
          {pending && !doneClicked && <LoaderCircle size={18} className="animate-spin" />}
          {t("academics.duty.saveOnly")}
        </button>
        {!isDone && (
          <button name="done" value="1" className="btn btn-green flex-1 py-3 shadow-card" disabled={pending} onClick={() => setDoneClicked(true)}>
            {pending && doneClicked ? <LoaderCircle size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
            {t("academics.duty.saveDone")}
          </button>
        )}
      </div>
    </form>
  );
}

function Count({ label, value, className }: { label: string; value: number; className: string }) {
  return (
    <div className="rounded-field bg-card px-2 py-1.5 text-center shadow-card">
      <p className={`text-lg leading-tight font-extrabold ${className}`}>{value}</p>
      <p className="text-[10.5px] font-semibold text-muted">{label}</p>
    </div>
  );
}
