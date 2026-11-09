import "server-only";
import { adminClient } from "./supabase/admin";
import type { Notification } from "./types";

export async function unreadCount(userId: string): Promise<number> {
  const { count } = await adminClient()
    .from("notifications")
    .select("id", { count: "exact", head: true })
    .eq("user_id", userId)
    .is("read_at", null);
  return count ?? 0;
}

export async function listNotifications(userId: string, limit = 60): Promise<Notification[]> {
  const { data } = await adminClient()
    .from("notifications")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as Notification[];
}
