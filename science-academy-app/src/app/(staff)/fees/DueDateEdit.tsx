"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, LoaderCircle, Pencil } from "lucide-react";
import { useT } from "@/components/I18nProvider";
import { dateLabel } from "@/lib/format";
import { changeDueDate } from "./actions";

/**
 * "Due 10 Nov ✏️": shows a fee row's due date and, for Admin/Reception,
 * lets them give more time by picking a new date right there.
 */
export function DueDateEdit({ rowId, due, canEdit, compact = false }: { rowId: string; due: string; canEdit: boolean; compact?: boolean }) {
  const t = useT();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(due);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  if (!open) {
    return (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <span className={compact ? "text-xs text-muted" : ""}>{t("fees.due.label", { date: dateLabel(due) })}</span>
        {canEdit && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setValue(due);
              setError(null);
              setOpen(true);
            }}
            className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[12px] font-bold text-primary hover:bg-primary-soft"
            aria-label={t("fees.due.change")}
            title={t("fees.due.change")}
          >
            <Pencil size={13} /> {compact ? "" : t("fees.due.change")}
          </button>
        )}
      </span>
    );
  }
  return (
    <span
      className="inline-flex flex-wrap items-center gap-1.5 rounded-field bg-primary-soft/60 p-2"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
    >
      <CalendarClock size={15} className="text-primary" aria-hidden />
      <span className="text-[12px] font-bold text-navy">{t("fees.due.giveTime")}</span>
      <input type="date" className="field w-auto py-1 text-[14px]" value={value} onChange={(e) => setValue(e.target.value)} aria-label={t("fees.due.change")} />
      <button
        type="button"
        className="btn btn-primary px-3 py-1 text-[13px]"
        disabled={pending || !value}
        onClick={() =>
          start(async () => {
            const res = await changeDueDate(rowId, value);
            if (!res.ok) setError(res.error);
            else {
              setOpen(false);
              router.refresh();
            }
          })
        }
      >
        {pending ? <LoaderCircle size={14} className="animate-spin" /> : null} {t("fees.due.save")}
      </button>
      <button type="button" className="btn btn-ghost px-3 py-1 text-[13px]" onClick={() => setOpen(false)}>
        {t("fees.due.cancel")}
      </button>
      {error && <span className="w-full text-[12px] font-semibold text-danger">{error}</span>}
    </span>
  );
}
