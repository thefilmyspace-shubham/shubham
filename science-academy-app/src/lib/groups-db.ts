import "server-only";
import { adminClient } from "./supabase/admin";
import { childrenOf, type Viewer } from "./auth";
import { allBatches, batchMap } from "./batches";
import { ensureParentUser } from "./notify";
import { canDeleteMessage, seenSummary, staffCanPost, staffCanRead, tickState } from "./groups";
import { getT } from "./i18n/server";
import type { AppUser, Batch, Group, Message } from "./types";

export type GroupView = Group & { batch: Batch | null; canPost: boolean };

async function extraGroupIds(userId: string): Promise<Set<string>> {
  const { data } = await adminClient().from("group_members").select("group_id").eq("user_id", userId);
  return new Set(((data ?? []) as { group_id: string }[]).map((r) => r.group_id));
}

async function parentBatchIds(viewer: Viewer): Promise<Set<string>> {
  const kids = await childrenOf(viewer.user);
  return new Set(kids.filter((k) => k.status === "active" && k.batch_id).map((k) => k.batch_id as string));
}

function who(viewer: Viewer) {
  return { role: viewer.user.role, perms: viewer.perms };
}

/** The groups this person may read, in order: staff groups first, then batch groups (Board, Class, Batch). */
export async function readableGroups(viewer: Viewer): Promise<GroupView[]> {
  const db = adminClient();
  const [{ data }, batches, extras, parentBatches] = await Promise.all([
    db.from("groups").select("*"),
    allBatches(true),
    extraGroupIds(viewer.user.id),
    viewer.user.role === "parent" ? parentBatchIds(viewer) : Promise.resolve(new Set<string>()),
  ]);
  const bm = batchMap(batches);
  const order = batches.map((b) => b.id);
  const out: GroupView[] = [];
  for (const g of (data ?? []) as Group[]) {
    const batch = g.batch_id ? (bm.get(g.batch_id) ?? null) : null;
    if (g.kind === "batch" && batch && !batch.active && viewer.user.role === "parent") continue;
    const readable =
      extras.has(g.id) ||
      (viewer.user.role === "parent" ? g.kind === "batch" && parentBatches.has(g.batch_id ?? "") : staffCanRead(who(viewer), g.kind));
    if (!readable) continue;
    out.push({ ...g, batch, canPost: staffCanPost(who(viewer), g.kind) });
  }
  const rank = (g: GroupView) => (g.kind === "management" ? -2 : g.kind === "faculty" ? -1 : order.indexOf(g.batch_id ?? ""));
  return out.sort((a, b) => rank(a) - rank(b));
}

export async function groupFor(viewer: Viewer, id: string): Promise<GroupView | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const groups = await readableGroups(viewer);
  return groups.find((g) => g.id === id) ?? null;
}

/** Last message and unread count per group (messages from the last 60 days). */
export async function groupSummaries(
  viewer: Viewer,
  groupIds: string[],
): Promise<Map<string, { last: (Message & { senderName: string }) | null; unread: number }>> {
  const out = new Map<string, { last: (Message & { senderName: string }) | null; unread: number }>();
  for (const id of groupIds) out.set(id, { last: null, unread: 0 });
  if (!groupIds.length) return out;
  const db = adminClient();
  const since = new Date(Date.now() - 60 * 86_400_000).toISOString();
  const [{ data: msgs }, { data: reads }] = await Promise.all([
    db.from("messages").select("*").in("group_id", groupIds).gte("created_at", since).order("created_at", { ascending: false }).limit(3000),
    db.from("message_reads").select("message_id").eq("user_id", viewer.user.id).gte("read_at", since),
  ]);
  const read = new Set(((reads ?? []) as { message_id: string }[]).map((r) => r.message_id));
  const list = (msgs ?? []) as Message[];
  const senders = await usersById([...new Set(list.map((m) => m.sender_id))]);
  for (const m of list) {
    const s = out.get(m.group_id);
    if (!s) continue;
    if (!s.last) s.last = { ...m, senderName: senders.get(m.sender_id)?.name ?? "" };
    if (m.sender_id !== viewer.user.id && !read.has(m.id)) s.unread++;
  }
  return out;
}

export async function usersById(ids: string[]): Promise<Map<string, AppUser>> {
  if (!ids.length) return new Map();
  const { data } = await adminClient().from("users").select("*").in("id", ids);
  return new Map(((data ?? []) as AppUser[]).map((u) => [u.id, u]));
}

/**
 * Parent logins of a batch: the login numbers of its active students. Makes
 * a missing login row so every parent can be notified.
 */
export async function batchParentIds(batchId: string, create = false): Promise<string[]> {
  const db = adminClient();
  const { data: students } = await db.from("students").select("id").eq("batch_id", batchId).eq("status", "active");
  const sids = ((students ?? []) as { id: string }[]).map((s) => s.id);
  if (!sids.length) return [];
  const { data: guardians } = await db
    .from("guardians")
    .select("mobile, name")
    .in("student_id", sids)
    .eq("is_login_number", true);
  const byMobile = new Map<string, string>();
  for (const g of (guardians ?? []) as { mobile: string; name: string | null }[]) byMobile.set(g.mobile, g.name ?? "Parent");
  if (!byMobile.size) return [];
  const { data: users } = await db.from("users").select("id, mobile").eq("role", "parent").in("mobile", [...byMobile.keys()]);
  const found = new Map(((users ?? []) as { id: string; mobile: string }[]).map((u) => [u.mobile, u.id]));
  if (create) {
    for (const [mobile, name] of byMobile) {
      if (found.has(mobile)) continue;
      const u = await ensureParentUser(mobile, name);
      if (u) found.set(mobile, u.id);
    }
  }
  return [...found.values()];
}

/** How many staff can read a staff group (for ✓✓ on your own messages). */
async function staffAudience(kind: Group["kind"]): Promise<string[]> {
  const roles = kind === "management" ? ["admin", "management", "reception"] : ["admin", "management", "reception", "faculty"];
  const { data } = await adminClient().from("users").select("id").in("role", roles).eq("status", "active");
  return ((data ?? []) as { id: string }[]).map((u) => u.id);
}

export type ChatMessage = Message & {
  senderName: string;
  senderTag: string;
  mine: boolean;
  ticks: 1 | 2 | 3 | null;
  seen: { seen: number; total: number } | null;
  canDelete: boolean;
};

/** The latest messages of a group, oldest first, with read info for staff. */
export async function loadChat(viewer: Viewer, group: GroupView, limit = 200): Promise<ChatMessage[]> {
  const db = adminClient();
  const { data } = await db
    .from("messages")
    .select("*")
    .eq("group_id", group.id)
    .order("created_at", { ascending: false })
    .limit(limit);
  const list = ((data ?? []) as Message[]).reverse();
  const senders = await usersById([...new Set(list.map((m) => m.sender_id))]);
  const isStaff = viewer.user.role !== "parent";

  // Read receipts: staff see "seen by" on batch posts and ticks on their own messages.
  let readers = new Map<string, Set<string>>();
  let parents: string[] = [];
  let audience: string[] = [];
  if (isStaff && list.length) {
    const { data: reads } = await db
      .from("message_reads")
      .select("message_id, user_id")
      .in("message_id", list.map((m) => m.id));
    readers = new Map();
    for (const r of (reads ?? []) as { message_id: string; user_id: string }[]) {
      if (!readers.has(r.message_id)) readers.set(r.message_id, new Set());
      readers.get(r.message_id)!.add(r.user_id);
    }
    if (group.kind === "batch" && group.batch_id) parents = await batchParentIds(group.batch_id);
    else audience = await staffAudience(group.kind);
  }

  return list.map((m) => {
    const sender = senders.get(m.sender_id);
    const mine = m.sender_id === viewer.user.id;
    const r = readers.get(m.id) ?? new Set<string>();
    const others = audience.filter((id) => id !== m.sender_id);
    return {
      ...m,
      senderName: sender?.name ?? "Unknown",
      senderTag: sender?.staff_id ?? (sender?.role === "parent" ? "Parent" : ""),
      mine,
      ticks: isStaff && mine && group.kind !== "batch" ? tickState([...r].filter((id) => others.includes(id)).length, others.length) : null,
      seen: isStaff && group.kind === "batch" ? seenSummary(r, parents) : null,
      canDelete: canDeleteMessage(viewer.user.role, mine),
    };
  });
}

/** Marks messages of a group as read by this person (not their own). */
export async function markGroupRead(viewer: Viewer, groupId: string): Promise<void> {
  const db = adminClient();
  const { data } = await db
    .from("messages")
    .select("id, sender_id")
    .eq("group_id", groupId)
    .order("created_at", { ascending: false })
    .limit(200);
  const rows = ((data ?? []) as { id: string; sender_id: string }[])
    .filter((m) => m.sender_id !== viewer.user.id)
    .map((m) => ({ message_id: m.id, user_id: viewer.user.id }));
  if (!rows.length) return;
  await db.from("message_reads").upsert(rows, { onConflict: "message_id,user_id", ignoreDuplicates: true });
}

export type Reader = { name: string; detail: string; at: string | null };

/**
 * Who has seen a message and who has not yet (staff only). Batch groups list
 * the batch's parents with their children's names; staff groups list the staff
 * who can read the group.
 */
export async function messageReaders(
  viewer: Viewer,
  messageId: string,
): Promise<{ seen: Reader[]; notSeen: Reader[]; audience: "parents" | "staff" } | null> {
  if (viewer.user.role === "parent" || !/^[0-9a-f-]{36}$/i.test(messageId)) return null;
  const db = adminClient();
  const { data: msg } = await db.from("messages").select("id, group_id, sender_id").eq("id", messageId).maybeSingle<{ id: string; group_id: string; sender_id: string }>();
  if (!msg) return null;
  const group = await groupFor(viewer, msg.group_id);
  if (!group) return null;

  const { data: reads } = await db.from("message_reads").select("user_id, read_at").eq("message_id", msg.id);
  const readAt = new Map(((reads ?? []) as { user_id: string; read_at: string }[]).map((r) => [r.user_id, r.read_at]));

  let audience: string[];
  const detail = new Map<string, string>();
  if (group.kind === "batch" && group.batch_id) {
    audience = await batchParentIds(group.batch_id);
    // Child names for each parent login in this batch.
    const users = await usersById(audience);
    const mobiles = [...users.values()].map((u) => u.mobile);
    const { data: links } = await db
      .from("guardians")
      .select("mobile, students!inner(name, batch_id, status)")
      .eq("is_login_number", true)
      .in("mobile", mobiles.length ? mobiles : ["-"])
      .eq("students.batch_id", group.batch_id)
      .eq("students.status", "active");
    const kids = new Map<string, string[]>();
    for (const l of (links ?? []) as unknown as { mobile: string; students: { name: string } | { name: string }[] }[]) {
      const names = Array.isArray(l.students) ? l.students.map((x) => x.name) : [l.students.name];
      kids.set(l.mobile, [...(kids.get(l.mobile) ?? []), ...names]);
    }
    const { t } = await getT();
    for (const u of users.values()) detail.set(u.id, kids.get(u.mobile)?.length ? t("groups.parentOf", { names: kids.get(u.mobile)!.join(", ") }) : t("core.role.parent"));
  } else {
    audience = await staffAudience(group.kind);
  }
  audience = audience.filter((id) => id !== msg.sender_id);
  const people = await usersById(audience);
  const row = (id: string): Reader => {
    const u = people.get(id);
    return {
      name: u?.name ?? "Unknown",
      detail: detail.get(id) ?? (u?.staff_id ? `${u.staff_id}` : ""),
      at: readAt.get(id) ?? null,
    };
  };
  const seen = audience.filter((id) => readAt.has(id)).map(row).sort((a, b) => (b.at ?? "").localeCompare(a.at ?? ""));
  const notSeen = audience.filter((id) => !readAt.has(id)).map(row).sort((a, b) => a.name.localeCompare(b.name));
  return { seen, notSeen, audience: group.kind === "batch" ? "parents" : "staff" };
}
