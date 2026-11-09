"use client";

import { useActionState } from "react";
import { LoaderCircle } from "lucide-react";

export type ActionResult = { ok: boolean; message: string } | null;

/**
 * A one-button form for a server action, with the result shown under it.
 * Hidden fields are passed as `fields`.
 */
export function ActionForm({
  action,
  fields,
  label,
  className = "btn btn-soft",
  confirm,
  icon,
}: {
  action: (prev: ActionResult, formData: FormData) => Promise<ActionResult>;
  fields: Record<string, string>;
  label: string;
  className?: string;
  confirm?: string;
  icon?: React.ReactNode;
}) {
  const [state, run, pending] = useActionState(action, null);
  return (
    <form
      action={run}
      onSubmit={(e) => {
        if (confirm && !window.confirm(confirm)) e.preventDefault();
      }}
      className="inline-flex max-w-full flex-col items-start gap-1"
    >
      {Object.entries(fields).map(([k, v]) => (
        <input key={k} type="hidden" name={k} value={v} />
      ))}
      <button className={`${className} max-w-full whitespace-normal text-left`} disabled={pending}>
        {pending ? <LoaderCircle size={15} className="animate-spin" /> : icon}
        {label}
      </button>
      {state && <span className={`text-xs font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</span>}
    </form>
  );
}
