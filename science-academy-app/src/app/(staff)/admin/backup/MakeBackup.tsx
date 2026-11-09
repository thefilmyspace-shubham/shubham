"use client";

import { useActionState } from "react";
import { DatabaseBackup, LoaderCircle } from "lucide-react";
import { makeBackupNow, type BackupState } from "./actions";
import { useT } from "@/components/I18nProvider";

export function MakeBackup() {
  const t = useT();
  const [state, action, pending] = useActionState<BackupState, FormData>(makeBackupNow, { ok: false, message: null });
  return (
    <form action={action} className="flex flex-wrap items-center gap-3">
      <button className="btn btn-primary" disabled={pending}>
        {pending ? <LoaderCircle size={16} className="animate-spin" /> : <DatabaseBackup size={16} />}
        {pending ? t("admin.backup.making") : t("admin.backup.make")}
      </button>
      {state.message && <p className={`text-[13px] font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
    </form>
  );
}
