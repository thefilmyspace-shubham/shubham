"use client";

import { useActionState, useState } from "react";
import { Check, Copy, LoaderCircle, Send } from "lucide-react";
import { sendAttendanceAlert, type SaveState } from "../actions";

/** The ready message to the parent: edit, copy, or send privately to the parent's app. */
export function AlertMessage({ studentId, message }: { studentId: string; message: string }) {
  const [text, setText] = useState(message);
  const [copied, setCopied] = useState(false);
  const [state, action, pending] = useActionState<SaveState, FormData>(sendAttendanceAlert, null);
  return (
    <form action={action} className="mt-2 space-y-2">
      <input type="hidden" name="studentId" value={studentId} />
      <textarea name="message" rows={3} className="field text-[13.5px]" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="btn btn-ghost py-1.5 text-[13px]"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(text);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {
              /* clipboard blocked: the text is still selectable */
            }
          }}
        >
          {copied ? <Check size={15} /> : <Copy size={15} />} {copied ? "Copied" : "Copy"}
        </button>
        <button className="btn btn-soft py-1.5 text-[13px]" disabled={pending || state?.ok}>
          {pending ? <LoaderCircle size={15} className="animate-spin" /> : <Send size={15} />} Send to parent
        </button>
        {state && <span className={`text-xs font-semibold ${state.ok ? "text-ok" : "text-danger"}`}>{state.message}</span>}
      </div>
    </form>
  );
}
