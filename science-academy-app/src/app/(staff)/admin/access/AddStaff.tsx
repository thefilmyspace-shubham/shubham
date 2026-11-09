"use client";

import { useActionState } from "react";
import { UserPlus } from "lucide-react";
import { addStaff, type ActionState } from "./actions";
import { useT } from "@/components/I18nProvider";

export function AddStaff({ emailRequired }: { emailRequired: boolean }) {
  const t = useT();
  const [state, action, pending] = useActionState<ActionState, FormData>(addStaff, { ok: false, message: null, at: 0 });
  return (
    <form action={action} key={state.ok ? state.at : "form"} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <label className="label" htmlFor="staff-role">
          {t("admin.access.roleLabel")}
        </label>
        <select id="staff-role" name="role" className="field" defaultValue="faculty">
          <option value="faculty">{t("core.role.faculty")} (FC)</option>
          <option value="reception">{t("core.role.reception")} (RC)</option>
          <option value="management">{t("core.role.management")} (MG)</option>
          <option value="admin">{t("core.role.admin")} (AD)</option>
        </select>
      </div>
      <div>
        <label className="label" htmlFor="staff-name">
          {t("admin.access.name")}
        </label>
        <input id="staff-name" name="name" className="field" required minLength={2} placeholder={t("admin.access.fullName")} />
      </div>
      <div>
        <label className="label" htmlFor="staff-mobile">
          {t("admin.access.mobileLogin")}
        </label>
        <input id="staff-mobile" name="mobile" className="field" required inputMode="numeric" placeholder="98765 43210" />
      </div>
      <div>
        <label className="label" htmlFor="staff-email">{emailRequired ? t("admin.access.emailCode") : t("admin.access.emailOptional")}</label>
        <input id="staff-email" name="email" type="email" className="field" placeholder="name@example.com" required={emailRequired} />
      </div>
      <div className="flex flex-wrap items-center gap-3 sm:col-span-2 lg:col-span-4">
        <button className="btn btn-primary" disabled={pending}>
          <UserPlus size={16} /> {t("admin.access.addBtn")}
        </button>
        {state.message && <p className={`text-[13px] font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
      </div>
    </form>
  );
}
