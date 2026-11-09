"use server";

import { revalidatePath } from "next/cache";
import { can, canSeeStudent, childrenOf, getViewer, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { saveFile } from "@/lib/storage";
import { notify } from "@/lib/notify";
import { all } from "@/lib/i18n";
import { getT } from "@/lib/i18n/server";
import { ensureThread, markThreadRead, staffWithPermission, threadById } from "@/lib/queries";

const MAX_FILE = 10 * 1024 * 1024;

export type QueryResult = { ok: true } | { ok: false; error: string };

async function readMessage(formData: FormData, t: Awaited<ReturnType<typeof getT>>["t"]) {
  const body = String(formData.get("body") ?? "").trim().slice(0, 3000);
  const entry = formData.get("file");
  const file = entry instanceof File && entry.size > 0 ? entry : null;
  if (!body && !file) return { error: t("groups.query.writeOrAttach") } as const;
  if (file && file.size > MAX_FILE) return { error: t("groups.query.tooBig") } as const;
  return { body, file } as const;
}

async function insertMessage(threadId: string, senderId: string, body: string, file: File | null): Promise<boolean> {
  let attachment_path: string | null = null;
  if (file) {
    try {
      attachment_path = await saveFile("attachments", `queries/${threadId}`, file);
    } catch {
      return false;
    }
  }
  const { error } = await adminClient()
    .from("query_messages")
    .insert({ thread_id: threadId, sender_id: senderId, body, attachment_path, attachment_name: file ? file.name.slice(0, 120) : null });
  return !error;
}

/** A parent asks the academy about one of their own children. */
export async function sendParentQuery(studentId: string, formData: FormData): Promise<QueryResult> {
  const { t } = await getT();
  const viewer = await getViewer();
  if (!viewer || viewer.user.role !== "parent") return { ok: false, error: t("groups.query.failed") };
  const kids = await childrenOf(viewer.user);
  const child = kids.find((k) => k.id === studentId);
  if (!child) return { ok: false, error: t("groups.query.failed") };
  const msg = await readMessage(formData, t);
  if ("error" in msg) return { ok: false, error: msg.error ?? "" };
  const thread = await ensureThread(viewer.user.id, child.id);
  if (!thread) return { ok: false, error: t("groups.query.failed") };
  if (!(await insertMessage(thread.id, viewer.user.id, msg.body, msg.file))) return { ok: false, error: t("groups.query.failed") };
  const now = new Date().toISOString();
  await adminClient().from("query_threads").update({ last_message_at: now, last_from: "parent", status: "open" }).eq("id", thread.id);
  await markThreadRead(thread.id, viewer.user.id);
  const staff = await staffWithPermission("queries.reply");
  await notify(
    staff.map((u) => ({
      userId: u.id,
      kind: "parent_query",
      title: all("groups.query.notifyStaffTitle", { parent: viewer.user.name }),
      body: `${child.name}${child.code ? ` (${child.code})` : ""}: ${msg.body ? msg.body.slice(0, 140) : "📎"}`,
      link: `/queries/${thread.id}`,
      dedupeKey: `query-${thread.id}-${now}`,
    })),
  );
  revalidatePath("/parent/query");
  return { ok: true };
}

/** Staff reply to a parent's query. */
export async function sendStaffReply(threadId: string, formData: FormData): Promise<QueryResult> {
  const { t } = await getT();
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "queries.reply")) return { ok: false, error: t("groups.query.notAllowed") };
  const thread = await threadById(threadId);
  if (!thread) return { ok: false, error: t("groups.query.failed") };
  const { data: student } = await adminClient().from("students").select("batch_id").eq("id", thread.student_id).maybeSingle();
  if (!student || !canSeeStudent(viewer, student)) return { ok: false, error: t("groups.query.notAllowed") };
  const msg = await readMessage(formData, t);
  if ("error" in msg) return { ok: false, error: msg.error ?? "" };
  if (!(await insertMessage(thread.id, viewer.user.id, msg.body, msg.file))) return { ok: false, error: t("groups.query.failed") };
  const now = new Date().toISOString();
  await adminClient().from("query_threads").update({ last_message_at: now, last_from: "staff" }).eq("id", thread.id);
  await markThreadRead(thread.id, viewer.user.id);
  await notify([
    {
      userId: thread.parent_user_id,
      kind: "query_reply",
      title: all("groups.query.notifyParentTitle"),
      body: msg.body ? msg.body.slice(0, 160) : all("groups.query.fileOnly"),
      link: "/parent/query",
      dedupeKey: `query-reply-${thread.id}-${now}`,
    },
  ]);
  revalidatePath(`/queries/${thread.id}`);
  revalidatePath("/queries");
  return { ok: true };
}

/** Mark a query resolved (or open again). */
export async function setQueryStatus(threadId: string, status: "open" | "resolved"): Promise<QueryResult> {
  const { t } = await getT();
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "queries.reply")) return { ok: false, error: t("groups.query.notAllowed") };
  const thread = await threadById(threadId);
  if (!thread) return { ok: false, error: t("groups.query.failed") };
  await adminClient().from("query_threads").update({ status }).eq("id", thread.id);
  revalidatePath(`/queries/${thread.id}`);
  revalidatePath("/queries");
  return { ok: true };
}

/** Opened the thread: messages so far count as read. */
export async function readQuery(threadId: string): Promise<void> {
  const viewer = await getViewer();
  if (!viewer) return;
  const thread = await threadById(threadId);
  if (!thread) return;
  if (viewer.user.role === "parent" ? thread.parent_user_id !== viewer.user.id : !can(viewer, "queries.reply")) return;
  await markThreadRead(thread.id, viewer.user.id);
}
