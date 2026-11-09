import "server-only";
import { adminClient } from "./supabase/admin";
import { resolvePermissions, type Overrides, type PermissionKey } from "./permissions";
import type { AppUser, Student } from "./types";

// Parent queries: one private thread per parent login and child, answered by
// staff with the "queries.reply" permission. No AI.

export type QueryThread = {
  id: string;
  parent_user_id: string;
  student_id: string;
  status: "open" | "resolved";
  last_message_at: string;
  last_from: "parent" | "staff";
  created_at: string;
};

export type QueryMessage = {
  id: string;
  thread_id: string;
  sender_id: string;
  body: string;
  attachment_path: string | null;
  attachment_name: string | null;
  created_at: string;
};

/** Active staff whose final permissions include `key` (role setting + their own). */
export async function staffWithPermission(key: PermissionKey): Promise<AppUser[]> {
  const db = adminClient();
  const [{ data: users }, { data: roleRows }, { data: userRows }] = await Promise.all([
    db.from("users").select("*").neq("role", "parent").eq("status", "active"),
    db.from("role_permissions").select("role, key, allowed").eq("key", key),
    db.from("user_permissions").select("user_id, key, allowed").eq("key", key),
  ]);
  const byRole = new Map<string, Overrides>();
  for (const r of (roleRows ?? []) as { role: string; key: PermissionKey; allowed: boolean }[]) byRole.set(r.role, { [r.key]: r.allowed });
  const byUser = new Map<string, Overrides>();
  for (const r of (userRows ?? []) as { user_id: string; key: PermissionKey; allowed: boolean }[]) byUser.set(r.user_id, { [r.key]: r.allowed });
  return ((users ?? []) as AppUser[]).filter((u) => resolvePermissions(u.role, byRole.get(u.role) ?? {}, byUser.get(u.id) ?? {})[key]);
}

export async function threadById(id: string): Promise<QueryThread | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const { data } = await adminClient().from("query_threads").select("*").eq("id", id).maybeSingle<QueryThread>();
  return data ?? null;
}

/** The parent's thread about one child (null until the first message). */
export async function threadOf(parentUserId: string, studentId: string): Promise<QueryThread | null> {
  const { data } = await adminClient()
    .from("query_threads")
    .select("*")
    .eq("parent_user_id", parentUserId)
    .eq("student_id", studentId)
    .maybeSingle<QueryThread>();
  return data ?? null;
}

export async function ensureThread(parentUserId: string, studentId: string): Promise<QueryThread | null> {
  const existing = await threadOf(parentUserId, studentId);
  if (existing) return existing;
  const { data } = await adminClient()
    .from("query_threads")
    .upsert({ parent_user_id: parentUserId, student_id: studentId }, { onConflict: "parent_user_id,student_id", ignoreDuplicates: true })
    .select("*")
    .maybeSingle<QueryThread>();
  return data ?? (await threadOf(parentUserId, studentId));
}

export type ChatLine = QueryMessage & { senderName: string; senderRole: AppUser["role"] | null; senderStaffId: string | null };

export async function threadMessages(threadId: string, limit = 300): Promise<ChatLine[]> {
  const db = adminClient();
  const { data } = await db.from("query_messages").select("*").eq("thread_id", threadId).order("created_at", { ascending: false }).limit(limit);
  const list = ((data ?? []) as QueryMessage[]).reverse();
  const ids = [...new Set(list.map((m) => m.sender_id))];
  const { data: users } = ids.length ? await db.from("users").select("*").in("id", ids) : { data: [] };
  const byId = new Map(((users ?? []) as AppUser[]).map((u) => [u.id, u]));
  return list.map((m) => {
    const u = byId.get(m.sender_id);
    return { ...m, senderName: u?.name ?? "", senderRole: u?.role ?? null, senderStaffId: u?.staff_id ?? null };
  });
}

export async function markThreadRead(threadId: string, userId: string): Promise<void> {
  await adminClient()
    .from("query_reads")
    .upsert({ thread_id: threadId, user_id: userId, last_read_at: new Date().toISOString() }, { onConflict: "thread_id,user_id" });
}

export type InboxRow = {
  thread: QueryThread;
  student: Pick<Student, "id" | "name" | "code" | "current_class" | "board" | "batch_id"> | null;
  parent: AppUser | null;
  last: QueryMessage | null;
  unread: number;
};

/** Threads for the staff inbox, newest first, with unread counts for this staff member. */
export async function inbox(viewerId: string, status: "open" | "resolved" | "all"): Promise<InboxRow[]> {
  const db = adminClient();
  let q = db.from("query_threads").select("*").order("last_message_at", { ascending: false }).limit(300);
  if (status !== "all") q = q.eq("status", status);
  const { data: threads, error } = await q;
  if (error) return []; // migration not run yet
  const list = (threads ?? []) as QueryThread[];
  if (!list.length) return [];
  const tids = list.map((t) => t.id);
  const [{ data: students }, { data: parents }, { data: msgs }, { data: reads }] = await Promise.all([
    db.from("students").select("id, name, code, current_class, board, batch_id").in("id", [...new Set(list.map((t) => t.student_id))]),
    db.from("users").select("*").in("id", [...new Set(list.map((t) => t.parent_user_id))]),
    db.from("query_messages").select("*").in("thread_id", tids).order("created_at", { ascending: false }).limit(2000),
    db.from("query_reads").select("thread_id, last_read_at").eq("user_id", viewerId).in("thread_id", tids),
  ]);
  const sMap = new Map(((students ?? []) as InboxRow["student"][]).map((s) => [s!.id, s]));
  const pMap = new Map(((parents ?? []) as AppUser[]).map((p) => [p.id, p]));
  const readAt = new Map(((reads ?? []) as { thread_id: string; last_read_at: string }[]).map((r) => [r.thread_id, r.last_read_at]));
  const lastBy = new Map<string, QueryMessage>();
  const unread = new Map<string, number>();
  for (const m of (msgs ?? []) as QueryMessage[]) {
    if (!lastBy.has(m.thread_id)) lastBy.set(m.thread_id, m);
    const t = list.find((x) => x.id === m.thread_id);
    if (t && m.sender_id === t.parent_user_id && m.created_at > (readAt.get(m.thread_id) ?? "")) unread.set(m.thread_id, (unread.get(m.thread_id) ?? 0) + 1);
  }
  return list.map((t) => ({
    thread: t,
    student: sMap.get(t.student_id) ?? null,
    parent: pMap.get(t.parent_user_id) ?? null,
    last: lastBy.get(t.id) ?? null,
    unread: unread.get(t.id) ?? 0,
  }));
}

/** Unread staff replies for a parent's thread (for the parent tab badge). */
export async function parentUnread(thread: QueryThread | null, parentId: string): Promise<number> {
  if (!thread) return 0;
  const db = adminClient();
  const { data: read } = await db.from("query_reads").select("last_read_at").eq("thread_id", thread.id).eq("user_id", parentId).maybeSingle<{ last_read_at: string }>();
  let q = db.from("query_messages").select("id", { count: "exact", head: true }).eq("thread_id", thread.id).neq("sender_id", parentId);
  if (read) q = q.gt("created_at", read.last_read_at);
  const { count } = await q;
  return count ?? 0;
}
