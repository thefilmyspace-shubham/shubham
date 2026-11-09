"use client";

import { useActionState } from "react";
import { UserPlus } from "lucide-react";
import { addStaff, type ActionState } from "./actions";

export function AddStaff() {
  const [state, action, pending] = useActionState<ActionState, FormData>(addStaff, { ok: false, message: null, at: 0 });
  return (
    <form action={action} key={state.ok ? state.at : "form"} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <label className="label" htmlFor="staff-role">Role</label>
        <select id="staff-role" name="role" className="field" defaultValue="faculty">
          <option value="faculty">Faculty (FC)</option>
          <option value="reception">Reception (RC)</option>
          <option value="management">Management (MG)</option>
          <option value="admin">Admin (AD)</option>
        </select>
      </div>
      <div>
        <label className="label" htmlFor="staff-name">Name</label>
        <input id="staff-name" name="name" className="field" required minLength={2} placeholder="Full name" />
      </div>
      <div>
        <label className="label" htmlFor="staff-mobile">Mobile (login)</label>
        <input id="staff-mobile" name="mobile" className="field" required inputMode="numeric" placeholder="98765 43210" />
      </div>
      <div>
        <label className="label" htmlFor="staff-email">Email (optional)</label>
        <input id="staff-email" name="email" type="email" className="field" placeholder="name@example.com" />
      </div>
      <div className="flex flex-wrap items-center gap-3 sm:col-span-2 lg:col-span-4">
        <button className="btn btn-primary" disabled={pending}>
          <UserPlus size={16} /> Add staff member
        </button>
        {state.message && <p className={`text-[13px] font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
      </div>
    </form>
  );
}
