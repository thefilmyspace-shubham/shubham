"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { FileText, LoaderCircle, Paperclip, Send, X } from "lucide-react";
import { browserClient } from "@/lib/supabase/browser";
import { dayLabel, timeLabel, todayIst } from "@/lib/format";
import { useT } from "../I18nProvider";
import { readQuery, sendParentQuery, sendStaffReply } from "./actions";

export type QueryLine = {
  id: string;
  mine: boolean;
  /** Who wrote it, as the reader should see it ("Science Academy · Pooja, Reception"). */
  from: string;
  body: string;
  attachment: string | null;
  createdAt: string;
};

/**
 * The private query chat. Parents send with `studentId`; staff reply with
 * `threadId`. New messages arrive live (realtime), else every 10 seconds.
 */
export function QueryChat({
  lines,
  threadId,
  mode,
  studentId,
}: {
  lines: QueryLine[];
  threadId: string | null;
  mode: "parent" | "staff";
  studentId?: string;
}) {
  const t = useT();
  const router = useRouter();
  const endRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [live, setLive] = useState(false);

  useEffect(() => {
    if (!threadId) return;
    const supabase = browserClient();
    const channel = supabase
      .channel(`query-${threadId}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "query_messages", filter: `thread_id=eq.${threadId}` }, () => router.refresh())
      .subscribe((status) => setLive(status === "SUBSCRIBED"));
    return () => {
      void supabase.removeChannel(channel);
    };
  }, [threadId, router]);

  useEffect(() => {
    if (live) return;
    const timer = setInterval(() => router.refresh(), 10_000);
    return () => clearInterval(timer);
  }, [live, router]);

  const count = lines.length;
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
    if (threadId) void readQuery(threadId);
  }, [threadId, count]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pending) return;
    const fd = new FormData();
    fd.set("body", body);
    if (file) fd.set("file", file);
    setError(null);
    start(async () => {
      const res = mode === "parent" ? await sendParentQuery(studentId ?? "", fd) : await sendStaffReply(threadId ?? "", fd);
      if (!res.ok) {
        setError(res.error);
        return;
      }
      setBody("");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      router.refresh();
    });
  }

  const days = lines.map((l) => todayIst(new Date(l.createdAt)));
  return (
    <div className="flex flex-col">
      <div className="min-h-[50dvh] space-y-1.5 bg-chat px-3 py-4 lg:rounded-t-card lg:px-6">
        {lines.length === 0 && <p className="px-4 py-10 text-center text-sm text-muted">{t("groups.query.empty")}</p>}
        {lines.map((l, i) => (
          <div key={l.id}>
            {(i === 0 || days[i] !== days[i - 1]) && (
              <div className="my-3 flex justify-center">
                <span className="rounded-full bg-card/90 px-3 py-1 text-[11.5px] font-bold text-muted shadow-card">
                  {days[i] === todayIst() ? t("core.today") : dayLabel(days[i])}
                </span>
              </div>
            )}
            <div className={`flex ${l.mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-2xl px-3 pt-2 pb-1.5 shadow-card lg:max-w-[70%] ${l.mine ? "rounded-br-md bg-bubble-out" : "rounded-bl-md bg-bubble-in"}`}>
                {!l.mine && <p className="text-[12.5px] font-bold text-primary">{l.from}</p>}
                {l.body && <p className="text-[14.5px] leading-snug break-words whitespace-pre-wrap text-fg">{l.body}</p>}
                {l.attachment && (
                  <a href={`/api/queries/attachment/${l.id}`} target="_blank" rel="noopener" className="mt-1.5 flex items-center gap-2 rounded-field bg-black/5 px-2.5 py-2 text-[13px] font-semibold text-primary">
                    <FileText size={16} className="shrink-0" />
                    <span className="truncate">{l.attachment}</span>
                  </a>
                )}
                <p className="mt-0.5 text-right text-[10.5px] text-faint">{timeLabel(l.createdAt)}</p>
              </div>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="safe-bottom sticky bottom-16 z-10 border-t border-line bg-card px-3 pt-2 pb-2 lg:bottom-0 lg:rounded-b-card">
        {file && (
          <div className="mb-2 flex items-center gap-2 rounded-field bg-field px-3 py-1.5 text-[13px]">
            <FileText size={15} className="text-primary" />
            <span className="min-w-0 flex-1 truncate">{file.name}</span>
            <button
              type="button"
              aria-label={t("groups.query.removeFile")}
              onClick={() => {
                setFile(null);
                if (fileRef.current) fileRef.current.value = "";
              }}
            >
              <X size={15} />
            </button>
          </div>
        )}
        {error && <p className="mb-2 text-[12.5px] font-semibold text-danger">{error}</p>}
        <div className="flex items-end gap-2">
          <input ref={fileRef} type="file" accept="image/*,application/pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button type="button" onClick={() => fileRef.current?.click()} className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-muted hover:bg-field" aria-label={t("groups.query.attach")}>
            <Paperclip size={20} />
          </button>
          <textarea
            className="field max-h-40 min-h-11 flex-1 resize-none py-2.5"
            rows={1}
            placeholder={mode === "parent" ? t("groups.query.placeholder") : t("groups.query.replyPlaceholder")}
            value={body}
            onChange={(e) => {
              setBody(e.target.value);
              if (error) setError(null);
            }}
          />
          <button className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-primary text-white disabled:opacity-50" disabled={pending || (!body.trim() && !file)} aria-label={t("groups.query.send")}>
            {pending ? <LoaderCircle size={19} className="animate-spin" /> : <Send size={19} />}
          </button>
        </div>
      </form>
    </div>
  );
}
