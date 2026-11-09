import "server-only";
import { adminClient } from "./supabase/admin";
import type { Role } from "./permissions";
import type { AppUser } from "./types";
import { asLang, pick, type Lang, type Localized } from "./i18n";

export type NewNotification = {
  userId: string;
  kind: string;
  /** Plain text, or the same text in every language (picked for each reader). */
  title: string | Localized;
  body?: string | Localized;
  link?: string;
  /** Same key for the same person is only ever sent once. */
  dedupeKey?: string;
};

/** In-app notifications (the bell). Duplicates by dedupe key are skipped. */
export async function notify(items: NewNotification[]): Promise<void> {
  if (!items.length) return;
  // Each reader's language, only when some text comes in several languages.
  const langs = new Map<string, Lang>();
  if (items.some((n) => typeof n.title !== "string" || (n.body !== undefined && typeof n.body !== "string"))) {
    const ids = [...new Set(items.map((n) => n.userId))];
    const { data } = await adminClient().from("users").select("*").in("id", ids);
    for (const u of (data ?? []) as AppUser[]) langs.set(u.id, asLang(u.language));
  }
  const rows = items.map((n) => ({
    user_id: n.userId,
    kind: n.kind,
    title: pick(n.title, langs.get(n.userId) ?? "en"),
    body: n.body === undefined ? null : pick(n.body, langs.get(n.userId) ?? "en"),
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
