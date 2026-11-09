"use client";

import { useActionState, useState } from "react";
import { Ban, LoaderCircle, Printer } from "lucide-react";
import type { ActionResult } from "../../fees/ActionForm";
import { cancelBill, logBillPrint } from "../actions";

/** Prints the office copy and the parent copy (two pages). */
export function PrintButton({ id }: { id: string }) {
  return (
    <button
      type="button"
      className="btn btn-ghost"
      onClick={() => {
        void logBillPrint(id);
        window.print();
      }}
    >
      <Printer size={16} /> Print (2 copies)
    </button>
  );
}

/** Admin only: cancel with a reason. The bill stays in the list as cancelled. */
export function CancelBill({ id, number }: { id: string; number: string }) {
  const [open, setOpen] = useState(false);
  const [state, run, pending] = useActionState<ActionResult, FormData>(cancelBill, null);
  if (!open) {
    return (
      <button type="button" className="btn btn-danger" onClick={() => setOpen(true)}>
        <Ban size={16} /> Cancel bill
      </button>
    );
  }
  return (
    <form
      action={run}
      onSubmit={(e) => {
        if (!window.confirm(`Cancel bill ${number}? It stays in the list as cancelled and cannot be undone.`)) e.preventDefault();
      }}
      className="w-full rounded-card border border-danger-line bg-danger-soft p-3"
    >
      <input type="hidden" name="id" value={id} />
      <label className="label text-danger" htmlFor="reason">
        Reason for cancelling (required)
      </label>
      <textarea id="reason" name="reason" required minLength={3} rows={2} className="field" placeholder="e.g. Wrong amount entered, new bill SA-26-0413 made" />
      {state && <p className={`mt-1 text-sm font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
      <div className="mt-2 flex gap-2">
        <button className="btn bg-danger text-white" disabled={pending}>
          {pending && <LoaderCircle size={15} className="animate-spin" />} Cancel this bill
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>
          Keep it
        </button>
      </div>
    </form>
  );
}
