"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import { LoaderCircle, SendHorizontal } from "lucide-react";
import { ask, type AskState } from "./actions";
import { useT } from "@/components/I18nProvider";

/** Question box + suggestion chips. One question at a time. */
export function Composer({ suggestions }: { suggestions: string[] }) {
  const t = useT();
  const [state, action, pending] = useActionState<AskState, FormData>(ask, { error: null, at: 0 });
  const [text, setText] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    // Keep the newest message in view.
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }, [state, pending]);

  return (
    <div className="safe-bottom sticky bottom-0 z-10 border-t border-line bg-card/95 px-4 pt-2 pb-3 backdrop-blur lg:px-8">
      {suggestions.length > 0 && (
        <div className="-mx-4 mb-2 flex gap-2 overflow-x-auto px-4 lg:mx-0 lg:flex-wrap lg:px-0">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              disabled={pending}
              onClick={() => {
                setText(s);
                requestAnimationFrame(() => formRef.current?.requestSubmit());
              }}
              className="shrink-0 rounded-full border border-line bg-card px-3 py-1.5 text-[12.5px] font-semibold text-primary hover:border-primary"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      {pending && (
        <p className="mb-2 flex items-center gap-2 text-[13px] text-muted">
          <LoaderCircle size={15} className="animate-spin" /> {t("admin.ai.lookingUp")}
        </p>
      )}
      {state.error && <p className="mb-2 text-[13px] font-semibold text-danger">{state.error}</p>}
      <form
        ref={formRef}
        action={(fd) => {
          // The question shows in the conversation once saved; the box clears at once.
          setText("");
          action(fd);
        }}
        className="flex items-end gap-2">
        <textarea
          name="text"
          rows={1}
          className="field max-h-32 min-h-11 resize-none"
          placeholder={t("admin.ai.placeholder")}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (text.trim() && !pending) formRef.current?.requestSubmit();
            }
          }}
          maxLength={2000}
        />
        <button className="btn btn-primary h-11 w-11 shrink-0 p-0" disabled={pending || !text.trim()} aria-label={t("groups.send")}>
          <SendHorizontal size={18} />
        </button>
      </form>
    </div>
  );
}
