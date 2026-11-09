"use client";

import { useActionState } from "react";
import { Save } from "lucide-react";
import { saveBatch, type BatchState } from "./actions";
import { useT } from "@/components/I18nProvider";

export type BatchValues = { id?: string; board: "CB" | "MP"; class: number; name: string; start_time: string | null };

export function BatchForm({ batch }: { batch?: BatchValues }) {
  const t = useT();
  const [state, action, pending] = useActionState<BatchState, FormData>(saveBatch, { ok: false, message: null, at: 0 });
  return (
    <form action={action} key={!batch && state.ok ? state.at : "f"} className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {batch?.id && <input type="hidden" name="id" value={batch.id} />}
      <div>
        <label className="label">{t("admin.batches.board")}</label>
        <select name="board" className="field" defaultValue={batch?.board ?? "CB"}>
          <option value="CB">CBSE</option>
          <option value="MP">MP Board</option>
        </select>
      </div>
      <div>
        <label className="label">{t("admin.batches.class")}</label>
        <select name="class" className="field" defaultValue={batch?.class ?? 10}>
          {[6, 7, 8, 9, 10, 11, 12].map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">{t("admin.batches.name")}</label>
        <input name="name" className="field" required placeholder="PCB" defaultValue={batch?.name ?? ""} />
      </div>
      <div>
        <label className="label">{t("admin.batches.time")}</label>
        <input name="start_time" className="field" placeholder="8:00 AM" defaultValue={batch?.start_time ?? ""} />
      </div>
      <div className="col-span-2 flex items-end md:col-span-1">
        <button className="btn btn-primary w-full" disabled={pending}>
          <Save size={16} /> {batch?.id ? t("core.save") : t("admin.batches.addBtn")}
        </button>
      </div>
      {state.message && <p className={`col-span-2 text-[13px] font-semibold md:col-span-5 ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</p>}
    </form>
  );
}
