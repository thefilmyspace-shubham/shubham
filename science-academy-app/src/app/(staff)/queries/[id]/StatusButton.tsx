"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, LoaderCircle, RotateCcw } from "lucide-react";
import { useT } from "@/components/I18nProvider";
import { setQueryStatus } from "@/components/query/actions";

export function StatusButton({ threadId, status }: { threadId: string; status: "open" | "resolved" }) {
  const t = useT();
  const router = useRouter();
  const [pending, start] = useTransition();
  const next = status === "open" ? "resolved" : "open";
  return (
    <button
      type="button"
      className={`btn py-1.5 text-[13px] ${status === "open" ? "btn-green" : "btn-ghost"}`}
      disabled={pending}
      onClick={() =>
        start(async () => {
          await setQueryStatus(threadId, next);
          router.refresh();
        })
      }
    >
      {pending ? <LoaderCircle size={15} className="animate-spin" /> : status === "open" ? <CheckCircle2 size={15} /> : <RotateCcw size={15} />}
      {status === "open" ? t("groups.query.markResolved") : t("groups.query.reopen")}
    </button>
  );
}
