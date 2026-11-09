"use client";

import { useMemo, useState, useTransition } from "react";
import { Lock, RotateCcw, Save } from "lucide-react";
import type { Role } from "@/lib/permissions";
import { resetRoleMatrix, saveRoleMatrix } from "./actions";

export type MatrixRow = {
  key: string;
  label: string;
  hint?: string;
  parent: string;
  cells: { role: Role; value: boolean; locked: boolean; isDefault: boolean }[];
};

const COLS: { role: Role; label: string }[] = [
  { role: "admin", label: "Admin" },
  { role: "management", label: "Management" },
  { role: "reception", label: "Reception" },
  { role: "faculty", label: "Faculty" },
];

/** Role × permission switches. Unsaved changes are highlighted until saved. */
export function Matrix({ rows }: { rows: MatrixRow[] }) {
  const initial = useMemo(() => Object.fromEntries(rows.flatMap((r) => r.cells.map((c) => [`${c.role}:${r.key}`, c.value]))), [rows]);
  const [values, setValues] = useState<Record<string, boolean>>(initial);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [pending, start] = useTransition();
  const changed = Object.keys(values).filter((k) => values[k] !== initial[k]);

  const save = () =>
    start(async () => {
      const cells = changed.map((k) => {
        const [role, key] = k.split(":");
        return { role: role as Role, key, allowed: values[k] };
      });
      const r = await saveRoleMatrix(cells);
      setMessage({ ok: r.ok, text: r.message ?? "" });
    });

  const reset = () => {
    if (!confirm("Put every role back to the default access? Per-person changes stay.")) return;
    start(async () => {
      const r = await resetRoleMatrix();
      setMessage({ ok: r.ok, text: r.message ?? "" });
    });
  };

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-card bg-card shadow-card">
        <table className="w-full min-w-[720px] text-left text-[13.5px]">
          <thead>
            <tr className="border-b border-line text-xs text-muted">
              <th className="px-4 py-2.5 font-semibold">What</th>
              {COLS.map((c) => (
                <th key={c.role} className="px-2 py-2.5 text-center font-semibold">
                  {c.label}
                </th>
              ))}
              <th className="px-3 py-2.5 font-semibold">Parent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.key}>
                <td className="px-4 py-2">
                  <p className="font-semibold">{r.label}</p>
                  {r.hint && <p className="text-[11.5px] text-muted">{r.hint}</p>}
                </td>
                {r.cells.map((c) => {
                  const id = `${c.role}:${r.key}`;
                  const on = values[id];
                  const dirty = on !== initial[id];
                  return (
                    <td key={c.role} className={`px-2 py-2 text-center ${dirty ? "bg-warn-soft" : ""}`}>
                      {c.locked ? (
                        <span className="inline-flex items-center gap-1 text-[12px] font-bold text-faint" title="Locked">
                          <Lock size={12} /> {on ? "Yes" : "No"}
                        </span>
                      ) : (
                        <button
                          type="button"
                          role="switch"
                          aria-checked={on}
                          aria-label={`${r.label} for ${c.role}`}
                          onClick={() => setValues((v) => ({ ...v, [id]: !v[id] }))}
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${on ? "bg-green" : "bg-line"}`}
                        >
                          <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${on ? "translate-x-5.5" : "translate-x-0.5"}`} />
                        </button>
                      )}
                      {!c.locked && !c.isDefault && !dirty && <span className="mt-0.5 block text-[10px] font-bold text-violet">changed</span>}
                    </td>
                  );
                })}
                <td className="px-3 py-2 text-[12px] text-muted">{r.parent}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button className="btn btn-primary" disabled={pending || changed.length === 0} onClick={save}>
          <Save size={16} /> Save{changed.length ? ` (${changed.length})` : ""}
        </button>
        {changed.length > 0 && (
          <button className="btn btn-ghost" disabled={pending} onClick={() => setValues(initial)}>
            Undo changes
          </button>
        )}
        <button className="btn btn-danger ml-auto" disabled={pending} onClick={reset}>
          <RotateCcw size={16} /> Reset to defaults
        </button>
      </div>
      {changed.length > 0 && <p className="text-[12.5px] font-semibold text-warn">Highlighted switches are not saved yet.</p>}
      {message && <p className={`text-[13px] font-semibold ${message.ok ? "text-ok" : "text-danger"}`}>{message.text}</p>}
    </div>
  );
}
