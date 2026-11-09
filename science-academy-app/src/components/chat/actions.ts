"use server";

import { getViewer, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { groupFor, batchParentIds, markGroupRead, messageReaders, type Reader } from "@/lib/groups-db";
import { canDeleteMessage, looksLikeFeeMessage } from "@/lib/groups";
import { getT } from "@/lib/i18n/server";
import { all } from "@/lib/i18n";
import { saveFile } from "@/lib/storage";
import { notify } from "@/lib/notify";
import { logActivity } from "@/lib/activity";
import type { MessageType } from "@/lib/types";

const MAX_FILE = 20 * 1024 * 1024;

export type SendResult = { ok: true } | { ok: false; error: string };

/** Sends a message (with an optional file) to a group the sender may write in. */
export async function sendMessage(groupId: string, formData: FormData): Promise<SendResult> {
  const { t } = await getT();
  const viewer = await staffForApi();
  if (!viewer) return { ok: false, error: t("groups.err.login") };
  const group = await groupFor(viewer, groupId);
  if (!group) return { ok: false, error: t("groups.err.notAvailable") };
  if (!group.canPost) {
    return {
      ok: false,
      error: group.kind === "batch" ? t("groups.err.batchOnly") : t("groups.err.cannotWrite"),
    };
  }

  const body = String(formData.get("body") ?? "").trim().slice(0, 4000);
  const fileEntry = formData.get("file");
  const file = fileEntry instanceof File && fileEntry.size > 0 ? fileEntry : null;
  if (!body && !file) return { ok: false, error: t("groups.err.empty") };
  if (file && file.size > MAX_FILE) return { ok: false, error: t("groups.err.fileSize") };

  let type: MessageType = "chat";
  if (group.kind === "batch") {
    const kind = String(formData.get("type") ?? "");
    if (kind !== "notice" && kind !== "timetable" && kind !== "test") return { ok: false, error: t("groups.err.type") };
    type = kind;
    if (looksLikeFeeMessage(`${body} ${file?.name ?? ""}`)) return { ok: false, error: t("groups.feeBlocked") };
  }

  let attachment_path: string | null = null;
  if (file) {
    try {
      attachment_path = await saveFile("attachments", `groups/${group.id}`, file);
    } catch (err) {
      console.error(err);
      return { ok: false, error: t("groups.err.upload") };
    }
  }

  const db = adminClient();
  const { data: msg, error } = await db
    .from("messages")
    .insert({
      group_id: group.id,
      sender_id: viewer.user.id,
      type,
      body,
      attachment_path,
      attachment_name: file ? file.name.slice(0, 120) : null,
    })
    .select("id")
    .single<{ id: string }>();
  if (error || !msg) return { ok: false, error: t("groups.err.send") };

  if (group.kind === "batch" && group.batch_id) {
    const parents = await batchParentIds(group.batch_id, true);
    const postKind = type === "chat" ? "notice" : type;
    const title = all(`groups.notify.${postKind}`, { group: group.name });
    await notify(
      parents.map((userId) => ({
        userId,
        kind: "group_post",
        title,
        body: body ? body.slice(0, 140) : (file?.name ?? undefined),
        link: "/parent",
        dedupeKey: `post-${msg.id}`,
      })),
    );
    await logActivity(viewer, "group.post", { type: "message", id: msg.id }, { group: group.name, type, parents: parents.length });
  }
  return { ok: true };
}

/** Marks the group's messages read for whoever is looking (staff or parent). */
export async function markRead(groupId: string): Promise<void> {
  const viewer = await getViewer();
  if (!viewer) return;
  const group = await groupFor(viewer, groupId);
  if (!group) return;
  await markGroupRead(viewer, group.id);
}

/** Who has seen a message (staff only). */
export async function getSeenBy(messageId: string): Promise<{ seen: Reader[]; notSeen: Reader[]; audience: "parents" | "staff" } | null> {
  const viewer = await staffForApi();
  if (!viewer) return null;
  return messageReaders(viewer, messageId);
}

/**
 * Deletes a message for everyone: the sender can delete their own, Admin can
 * delete any. Its file and the parents' notifications about it go too, and the
 * deletion is written to the activity log (with the text, for the record).
 */
export async function deleteMessage(messageId: string): Promise<SendResult> {
  const { t } = await getT();
  const viewer = await staffForApi();
  if (!viewer) return { ok: false, error: t("groups.err.login") };
  if (!/^[0-9a-f-]{36}$/i.test(messageId)) return { ok: false, error: t("groups.err.notFound") };
  const db = adminClient();
  const { data: msg } = await db.from("messages").select("*").eq("id", messageId).maybeSingle<{
    id: string; group_id: string; sender_id: string; type: MessageType; body: string; attachment_path: string | null; attachment_name: string | null; created_at: string;
  }>();
  if (!msg) return { ok: false, error: t("groups.err.gone") };
  const group = await groupFor(viewer, msg.group_id);
  if (!group) return { ok: false, error: t("groups.err.notAvailable") };
  if (!canDeleteMessage(viewer.user.role, msg.sender_id === viewer.user.id)) {
    return { ok: false, error: t("groups.err.deleteOwn") };
  }
  const { error } = await db.from("messages").delete().eq("id", msg.id);
  if (error) return { ok: false, error: t("groups.err.delete") };
  if (msg.attachment_path) await db.storage.from("attachments").remove([msg.attachment_path]).catch(() => null);
  await db.from("notifications").delete().eq("dedupe_key", `post-${msg.id}`);
  await logActivity(viewer, "group.delete", { type: "message", id: msg.id }, {
    group: group.name,
    sent_by: msg.sender_id === viewer.user.id ? "self" : msg.sender_id,
    sent_at: msg.created_at,
    type: msg.type,
    text: msg.body.slice(0, 300),
    file: msg.attachment_name,
  });
  return { ok: true };
}
