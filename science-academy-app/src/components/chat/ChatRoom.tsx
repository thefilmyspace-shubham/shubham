"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Check, CheckCheck, Eye, FileText, Info, LoaderCircle, Lock, Paperclip, Send, X } from "lucide-react";
import { browserClient } from "@/lib/supabase/browser";
import { dayLabel, timeLabel, todayIst } from "@/lib/format";
import { MESSAGE_TYPE_LABEL, POST_TYPES, looksLikeFeeMessage, FEE_BLOCKED_ERROR } from "@/lib/groups";
import type { ChatMessage } from "@/lib/groups-db";
import type { MessageType } from "@/lib/types";
import { markRead, sendMessage } from "./actions";

type Props = {
  groupId: string;
  messages: ChatMessage[];
  /** null = read only (with this bar text). */
  composer: { kind: "batch" | "staff"; warning: string } | null;
  readOnlyText?: string;
  showSenderTag?: boolean;
  /** false: no read-only bar at the bottom (the parent app shows it at the top). */
  bottomBar?: boolean;
};

const TYPE_TONE: Record<MessageType, string> = {
  chat: "",
  notice: "bg-primary-soft text-primary",
  timetable: "bg-green-soft text-ok",
  test: "bg-violet-soft text-violet",
};

export function ChatRoom({ groupId, messages, composer, readOnlyText, showSenderTag = true, bottomBar = true }: Props) {
  const router = useRouter();
  const endRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [body, setBody] = useState("");
  const [type, setType] = useState<Exclude<MessageType, "chat">>("notice");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [live, setLive] = useState(false);

  // New messages: realtime (RLS lets readers of this group see inserts); polling if that is not connected.
  useEffect(() => {
    const supabase = browserClient();
    const channel = supabase
      .channel(`group-${groupId}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "messages", filter: `group_id=eq.${groupId}` }, () => router.refresh())
      .subscribe((status) => setLive(status === "SUBSCRIBED"));
    return () => {
      void supabase.removeChannel(channel);
    };
  }, [groupId, router]);

  useEffect(() => {
    if (live) return;
    const t = setInterval(() => router.refresh(), 10_000);
    return () => clearInterval(t);
  }, [live, router]);

  const count = messages.length;
  const lastId = messages[count - 1]?.id;
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
    void markRead(groupId);
  }, [groupId, count, lastId]);

  const feeWarning = composer?.kind === "batch" && body.length > 0 && looksLikeFeeMessage(body);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!composer || pending) return;
    if (feeWarning) {
      setError(FEE_BLOCKED_ERROR);
      return;
    }
    const fd = new FormData();
    fd.set("body", body);
    if (composer.kind === "batch") fd.set("type", type);
    if (file) fd.set("file", file);
    setError(null);
    start(async () => {
      const res = await sendMessage(groupId, fd);
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

  const days = messages.map((m) => todayIst(new Date(m.created_at)));
  return (
    <div className={`flex flex-col ${bottomBar ? "min-h-[calc(100dvh-7.5rem)] lg:min-h-[calc(100dvh-9rem)]" : ""}`}>
      <div className="flex-1 space-y-1.5 bg-chat px-3 py-4 lg:rounded-card lg:px-6">
        {messages.length === 0 && <p className="py-10 text-center text-sm text-muted">No messages yet.</p>}
        {messages.map((m, i) => {
          const day = days[i];
          const sep = i === 0 || day !== days[i - 1];
          return (
            <div key={m.id}>
              {sep && (
                <div className="my-3 flex justify-center">
                  <span className="rounded-full bg-card/90 px-3 py-1 text-[11.5px] font-bold text-muted shadow-card">
                    {day === todayIst() ? "Today" : dayLabel(day)}
                  </span>
                </div>
              )}
              <Bubble m={m} showSenderTag={showSenderTag} />
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      {composer ? (
        <form onSubmit={submit} className="safe-bottom sticky bottom-0 z-10 border-t border-line bg-card px-3 pt-2 pb-2 lg:rounded-b-card">
          <p className={`mb-2 flex items-start gap-1.5 text-[12px] font-semibold ${composer.kind === "batch" ? "text-warn" : "text-muted"}`}>
            {composer.kind === "batch" ? <AlertTriangle size={14} className="mt-px shrink-0" /> : <Info size={14} className="mt-px shrink-0" />}
            {composer.warning}
          </p>
          {composer.kind === "batch" && (
            <div className="mb-2 flex gap-1.5" role="radiogroup" aria-label="Post type">
              {POST_TYPES.map((p) => (
                <button
                  key={p.type}
                  type="button"
                  role="radio"
                  aria-checked={type === p.type}
                  onClick={() => setType(p.type)}
                  className={`rounded-full border px-3 py-1 text-[12.5px] font-bold ${
                    type === p.type ? "border-primary bg-primary text-white" : "border-line bg-card text-fg"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}
          {file && (
            <div className="mb-2 flex items-center gap-2 rounded-field bg-field px-3 py-1.5 text-[13px]">
              <FileText size={15} className="text-primary" />
              <span className="min-w-0 flex-1 truncate">{file.name}</span>
              <button
                type="button"
                aria-label="Remove file"
                onClick={() => {
                  setFile(null);
                  if (fileRef.current) fileRef.current.value = "";
                }}
              >
                <X size={15} />
              </button>
            </div>
          )}
          {(error || feeWarning) && <p className="mb-2 text-[12.5px] font-semibold text-danger">{error ?? FEE_BLOCKED_ERROR}</p>}
          <div className="flex items-end gap-2">
            <input ref={fileRef} type="file" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-muted hover:bg-field"
              aria-label="Attach a file"
            >
              <Paperclip size={20} />
            </button>
            <textarea
              className="field max-h-40 min-h-11 flex-1 resize-none py-2.5"
              rows={1}
              placeholder={composer.kind === "batch" ? `Write a ${MESSAGE_TYPE_LABEL[type].toLowerCase()} for parents…` : "Message"}
              value={body}
              onChange={(e) => {
                setBody(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(min-width: 1024px)").matches) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <button
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-primary text-white disabled:opacity-50"
              disabled={pending || (!body.trim() && !file) || feeWarning}
              aria-label="Send"
            >
              {pending ? <LoaderCircle size={19} className="animate-spin" /> : <Send size={19} />}
            </button>
          </div>
        </form>
      ) : !bottomBar ? null : (
        <div className="safe-bottom sticky bottom-0 z-10 flex items-center justify-center gap-2 border-t border-line bg-card px-4 py-3 text-[13px] font-semibold text-muted lg:rounded-b-card">
          <Lock size={14} /> {readOnlyText ?? "Read only"}
        </div>
      )}
    </div>
  );
}

function Bubble({ m, showSenderTag }: { m: ChatMessage; showSenderTag: boolean }) {
  return (
    <div className={`flex ${m.mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3 pt-2 pb-1.5 shadow-card lg:max-w-[70%] ${
          m.mine ? "rounded-br-md bg-bubble-out" : "rounded-bl-md bg-bubble-in"
        }`}
      >
        {!m.mine && (
          <p className="text-[12.5px] font-bold text-primary">
            {m.senderName}
            {showSenderTag && m.senderTag && <span className="ml-1.5 font-semibold text-faint">{m.senderTag}</span>}
          </p>
        )}
        {m.type !== "chat" && (
          <span className={`mt-0.5 mb-1 inline-block rounded-full px-2 py-0.5 text-[10.5px] font-extrabold tracking-wide uppercase ${TYPE_TONE[m.type]}`}>
            {MESSAGE_TYPE_LABEL[m.type]}
          </span>
        )}
        {m.body && <p className="text-[14.5px] leading-snug break-words whitespace-pre-wrap text-fg">{m.body}</p>}
        {m.attachment_path && (
          <a
            href={`/api/groups/attachment/${m.id}`}
            target="_blank"
            rel="noopener"
            className="mt-1.5 flex items-center gap-2 rounded-field bg-black/5 px-2.5 py-2 text-[13px] font-semibold text-primary"
          >
            <FileText size={16} className="shrink-0" />
            <span className="truncate">{m.attachment_name ?? "File"}</span>
          </a>
        )}
        <div className="mt-0.5 flex items-center justify-end gap-1.5 text-[10.5px] text-faint">
          {m.seen && (
            <span className="inline-flex items-center gap-1 font-semibold">
              <Eye size={11} /> Seen by {m.seen.seen} of {m.seen.total} parents ·
            </span>
          )}
          {timeLabel(m.created_at)}
          {m.ticks === 1 && <Check size={13} aria-label="Sent" />}
          {m.ticks === 2 && <CheckCheck size={13} aria-label="Seen by some" />}
          {m.ticks === 3 && <CheckCheck size={13} className="text-seen" aria-label="Seen by everyone" />}
        </div>
      </div>
    </div>
  );
}
