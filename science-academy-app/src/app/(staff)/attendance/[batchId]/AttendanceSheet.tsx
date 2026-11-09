"use client";

import { useActionState, useMemo, useState } from "react";
import { CheckCheck, Lock, LoaderCircle } from "lucide-react";
import { saveAttendance, type SaveState } from "../actions";

type Status = "P" | "A" | "L";

export type SheetRow = {
  id: string;
  name: string;
  code: string | null;
  status: Status | null;
  /** Saved more than 24 hours ago. */
  locked: boolean;
  /** This viewer may change it. */
  editable: boolean;
};

const BTN: Record<Status, { on: string; label: string }> = {
  P: { on: "bg-green text-white border-green", label: "Present" },
  A: { on: "bg-danger text-white border-danger", label: "Absent" },
  L: { on: "bg-warn text-white border-warn", label: "Late" },
};

export function AttendanceSheet({
  batchId,
  date,
  rows,
  note,
  canEditNote,
  correcting,
}: {
  batchId: string;
  date: string;
  rows: SheetRow[];
  note: string;
  canEditNote: boolean;
  correcting: boolean;
}) {
  const [marks, setMarks] = useState<Record<string, Status | null>>(() => Object.fromEntries(rows.map((r) => [r.id, r.status])));
  const [state, action, pending] = useActionState<SaveState, FormData>(saveAttendance, null);
  const anyEditable = rows.some((r) => r.editable);

  const counts = useMemo(() => {
    const c = { P: 0, A: 0, L: 0, left: 0 };
    for (const r of rows) {
      const s = marks[r.id];
      if (s) c[s]++;
      else c.left++;
    }
    return c;
  }, [marks, rows]);

  const changed = rows.filter((r) => r.editable && marks[r.id] && marks[r.id] !== r.status);
  const entries = Object.fromEntries(rows.filter((r) => r.editable && marks[r.id]).map((r) => [r.id, marks[r.id]]));

  return (
    <form action={action} className="space-y-3">
      <input type="hidden" name="batchId" value={batchId} />
      <input type="hidden" name="date" value={date} />
      <input type="hidden" name="entries" value={JSON.stringify(entries)} />

      <div className="sticky top-14 z-[5] -mx-4 grid grid-cols-4 gap-2 bg-bg/95 px-4 py-2 backdrop-blur lg:static lg:mx-0 lg:px-0">
        <Count label="Present" value={counts.P} className="text-green" />
        <Count label="Absent" value={counts.A} className="text-danger" />
        <Count label="Late" value={counts.L} className="text-warn" />
        <Count label="Not marked" value={counts.left} className="text-muted" />
      </div>

      {anyEditable && (
        <div className="flex justify-end">
          <button
            type="button"
            className="btn btn-soft py-1.5 text-[13px]"
            onClick={() =>
              setMarks((m) => {
                const next = { ...m };
                for (const r of rows) if (r.editable && !next[r.id]) next[r.id] = "P";
                return next;
              })
            }
          >
            <CheckCheck size={15} /> All present (rest)
          </button>
        </div>
      )}

      <ul className="divide-y divide-line overflow-hidden rounded-card bg-card shadow-card">
        {rows.map((r, i) => {
          const current = marks[r.id];
          return (
            <li key={r.id} className="flex items-center gap-3 px-3 py-2.5 sm:px-4">
              <span className="w-6 shrink-0 text-right text-xs font-bold text-faint">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-semibold">{r.name}</p>
                <p className="flex items-center gap-1 text-[11.5px] text-muted">
                  {r.code}
                  {r.locked && (
                    <span className="inline-flex items-center gap-0.5 text-faint">
                      <Lock size={11} /> locked
                    </span>
                  )}
                </p>
              </div>
              <div className="flex shrink-0 gap-1.5">
                {(["P", "A", "L"] as Status[]).map((s) => (
                  <button
                    key={s}
                    type="button"
                    disabled={!r.editable}
                    aria-pressed={current === s}
                    aria-label={`${BTN[s].label}: ${r.name}`}
                    onClick={() => setMarks((m) => ({ ...m, [r.id]: s }))}
                    className={`h-11 w-11 rounded-full border-2 text-[15px] font-extrabold transition-colors disabled:cursor-not-allowed ${
                      current === s ? BTN[s].on : "border-line bg-card text-muted"
                    } ${!r.editable && current !== s ? "opacity-40" : ""}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </li>
          );
        })}
      </ul>

      <div>
        <label className="label" htmlFor="note">
          Note for this day (optional)
        </label>
        <textarea
          id="note"
          name="note"
          rows={2}
          defaultValue={note}
          disabled={!canEditNote}
          placeholder="For example: test period, 2 students left early"
          className="field"
        />
      </div>

      {state && <p className={`text-sm font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}

      {(anyEditable || canEditNote) && (
        <div className="sticky bottom-20 lg:bottom-4">
          <button className={`btn w-full py-3 shadow-card ${correcting ? "btn-primary" : "btn-green"}`} disabled={pending}>
            {pending && <LoaderCircle size={18} className="animate-spin" />}
            {correcting ? `Save correction${changed.length ? ` (${changed.length})` : ""}` : "Save attendance"}
          </button>
        </div>
      )}
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
