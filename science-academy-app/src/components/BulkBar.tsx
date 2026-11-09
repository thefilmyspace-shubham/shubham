"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CheckSquare, LoaderCircle, Trash2, X } from "lucide-react";
import { useT } from "./I18nProvider";

export type BulkResult = { ok: boolean; message: string };

/**
 * Select many → delete in one go. Put <BulkCheck group="tests" id="…" /> next
 * to each item, and one <BulkBar group="tests" action={…} /> on the page. The
 * bar appears at the bottom once something is ticked, asks to confirm, then
 * runs the server action with the ticked ids.
 */
export function BulkCheck({ group, id, label }: { group: string; id: string; label?: string }) {
  return (
    <input
      type="checkbox"
      data-bulk={group}
      value={id}
      aria-label={label}
      onClick={(e) => e.stopPropagation()}
      className="h-5 w-5 shrink-0 cursor-pointer accent-[var(--color-primary)]"
    />
  );
}

function boxes(group: string): HTMLInputElement[] {
  return Array.from(document.querySelectorAll<HTMLInputElement>(`input[data-bulk="${group}"]`));
}

export function BulkBar({ group, action }: { group: string; action: (ids: string[]) => Promise<BulkResult> }) {
  const t = useT();
  const router = useRouter();
  const [count, setCount] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [message, setMessage] = useState<BulkResult | null>(null);
  const [pending, start] = useTransition();

  const recount = useCallback(() => {
    setCount(boxes(group).filter((b) => b.checked).length);
    setConfirm(false);
  }, [group]);

  useEffect(() => {
    const onChange = (e: Event) => {
      if ((e.target as HTMLElement)?.dataset?.bulk === group) recount();
    };
    document.addEventListener("change", onChange);
    return () => document.removeEventListener("change", onChange);
  }, [group, recount]);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [message]);

  const clear = () => {
    boxes(group).forEach((b) => (b.checked = false));
    recount();
  };
  const selectAll = () => {
    boxes(group).forEach((b) => (b.checked = true));
    recount();
  };
  const run = () =>
    start(async () => {
      const ids = boxes(group)
        .filter((b) => b.checked)
        .map((b) => b.value);
      const res = await action(ids);
      setMessage(res);
      clear();
      router.refresh();
    });

  if (!count && !message) return null;
  return (
    <div className="no-print fixed inset-x-0 bottom-20 z-30 px-3 lg:bottom-4 lg:pl-64" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
      <div className="mx-auto flex max-w-xl flex-wrap items-center gap-2 rounded-2xl bg-navy px-4 py-3 text-white shadow-sheet">
        {message && !count ? (
          <p className={`flex-1 text-sm font-semibold ${message.ok ? "" : "text-[#ffb4ab]"}`}>{message.message}</p>
        ) : confirm ? (
          <>
            <p className="min-w-0 flex-1 text-sm font-semibold">{t("core.bulk.confirm", { n: count })}</p>
            <button type="button" className="btn bg-white/15 py-1.5 text-[13px] text-white" onClick={() => setConfirm(false)} disabled={pending}>
              {t("core.bulk.keep")}
            </button>
            <button type="button" className="btn bg-danger py-1.5 text-[13px] text-white" onClick={run} disabled={pending}>
              {pending ? <LoaderCircle size={15} className="animate-spin" /> : <Trash2 size={15} />} {t("core.bulk.deleteN", { n: count })}
            </button>
          </>
        ) : (
          <>
            <p className="min-w-0 flex-1 text-sm font-bold">{t("core.bulk.selected", { n: count })}</p>
            <button type="button" className="btn bg-white/15 px-2.5 py-1.5 text-[13px] text-white" onClick={selectAll} title={t("core.bulk.selectAll")}>
              <CheckSquare size={15} /> {t("core.bulk.selectAll")}
            </button>
            <button type="button" className="grid h-8 w-8 place-items-center rounded-full hover:bg-white/10" onClick={clear} aria-label={t("core.bulk.clear")}>
              <X size={17} />
            </button>
            <button type="button" className="btn bg-danger py-1.5 text-[13px] text-white" onClick={() => setConfirm(true)}>
              <Trash2 size={15} /> {t("core.bulk.delete")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
