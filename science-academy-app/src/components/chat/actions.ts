"use server";

import { getViewer, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { groupFor, batchParentIds, markGroupRead, messageReaders, type Reader } from "@/lib/groups-db";
import { FEE_BLOCKED_ERROR, MESSAGE_TYPE_LABEL, canDeleteMessage, looksLikeFeeMessage } from "@/lib/groups";
import { saveFile } from "@/lib/storage";
import { notify } from "@/lib/notify";
import { logActivity } from "@/lib/activity";
import type { MessageType } from "@/lib/types";

const MAX_FILE = 20 * 1024 * 1024;

export type SendResult = { ok: true } | { ok: false; error: string };

/** Sends a message (with an optional file) to a group the sender may write in. */
export async function sendMessage(groupId: string, formData: FormData): Promise<SendResult> {
  const viewer = await staffForApi();
  if (!viewer) return { ok: false, error: "Please log in again." };
  const group = await groupFor(viewer, groupId);
  if (!group) return { ok: false, error: "This group is not available." };
  if (!group.canPost) {
    return {
      ok: false,
      error: group.kind === "batch" ? "Only management and admin can post in batch groups." : "Your login cannot write in this group.",
    };
  }

  const body = String(formData.get("body") ?? "").trim().slice(0, 4000);
  const fileEntry = formData.get("file");
  const file = fileEntry instanceof File && fileEntry.size > 0 ? fileEntry : null;
  if (!body && !file) return { ok: false, error: "Write a message or attach a file." };
  if (file && file.size > MAX_FILE) return { ok: false, error: "Files can be up to 20 MB." };

  let type: MessageType = "chat";
  if (group.kind === "batch") {
    const t = String(formData.get("type") ?? "");
    if (t !== "notice" && t !== "timetable" && t !== "test") return { ok: false, error: "Choose Notice, Timetable or Test." };
    type = t;
    if (looksLikeFeeMessage(`${body} ${file?.name ?? ""}`)) return { ok: false, error: FEE_BLOCKED_ERROR };
  }

  let attachment_path: string | null = null;
  if (file) {
    try {
      attachment_path = await saveFile("attachments", `groups/${group.id}`, file);
    } catch (err) {
      console.error(err);
      return { ok: false, error: "Could not upload the file. Please try again." };
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
  if (error || !msg) return { ok: false, error: "Could not send. Please try again." };

  if (group.kind === "batch" && group.batch_id) {
    const parents = await batchParentIds(group.batch_id, true);
    const label = MESSAGE_TYPE_LABEL[type];
    await notify(
      parents.map((userId) => ({
        userId,
        kind: "group_post",
        title: `New ${label.toLowerCase()} in ${group.name}`,
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
  const viewer = await staffForApi();
  if (!viewer) return { ok: false, error: "Please log in again." };
  if (!/^[0-9a-f-]{36}$/i.test(messageId)) return { ok: false, error: "Message not found." };
  const db = adminClient();
  const { data: msg } = await db.from("messages").select("*").eq("id", messageId).maybeSingle<{
    id: string; group_id: string; sender_id: string; type: MessageType; body: string; attachment_path: string | null; attachment_name: string | null; created_at: string;
  }>();
  if (!msg) return { ok: false, error: "This message was already deleted." };
  const group = await groupFor(viewer, msg.group_id);
  if (!group) return { ok: false, error: "This group is not available." };
  if (!canDeleteMessage(viewer.user.role, msg.sender_id === viewer.user.id)) {
    return { ok: false, error: "You can delete only your own messages. Admin can delete any message." };
  }
  const { error } = await db.from("messages").delete().eq("id", msg.id);
  if (error) return { ok: false, error: "Could not delete. Please try again." };
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
