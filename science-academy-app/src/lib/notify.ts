import "server-only";
import { adminClient } from "./supabase/admin";
import type { Role } from "./permissions";
import type { AppUser } from "./types";

export type NewNotification = {
  userId: string;
  kind: string;
  title: string;
  body?: string;
  link?: string;
  /** Same key for the same person is only ever sent once. */
  dedupeKey?: string;
};

/** In-app notifications (the bell). Duplicates by dedupe key are skipped. */
export async function notify(items: NewNotification[]): Promise<void> {
  if (!items.length) return;
  const rows = items.map((n) => ({
    user_id: n.userId,
    kind: n.kind,
    title: n.title,
    body: n.body ?? null,
    link: n.link ?? null,
    dedupe_key: n.dedupeKey ?? null,
  }));
  const { error } = await adminClient()
    .from("notifications")
    .upsert(rows, { onConflict: "user_id,dedupe_key", ignoreDuplicates: true });
  if (error) console.error("notify failed", error.message);
}

export async function activeUsersWithRole(roles: Role[]): Promise<AppUser[]> {
  const { data } = await adminClient().from("users").select("*").in("role", roles).eq("status", "active");
  return (data ?? []) as AppUser[];
}

/**
 * The parent login of a student (their one login number). Creates the login
 * row if the number has none yet, so notifications always have somewhere to go.
 */
export async function parentUserOf(studentId: string): Promise<AppUser | null> {
  const db = adminClient();
  const { data: g } = await db
    .from("guardians")
    .select("mobile, name")
    .eq("student_id", studentId)
    .eq("is_login_number", true)
    .maybeSingle<{ mobile: string; name: string | null }>();
  if (!g) return null;
  return ensureParentUser(g.mobile, g.name ?? "Parent");
}

export async function ensureParentUser(mobile: string, name: string): Promise<AppUser | null> {
  const db = adminClient();
  const { data: existing } = await db
    .from("users")
    .select("*")
    .eq("mobile", mobile)
    .eq("role", "parent")
    .maybeSingle<AppUser>();
  if (existing) return existing;
  const { data, error } = await db
    .from("users")
    .insert({ role: "parent", name, mobile })
    .select("*")
    .single<AppUser>();
  if (error) {
    // Two requests at once: the other one made it.
    const { data: again } = await db.from("users").select("*").eq("mobile", mobile).eq("role", "parent").maybeSingle<AppUser>();
    return again ?? null;
  }
  return data;
}
