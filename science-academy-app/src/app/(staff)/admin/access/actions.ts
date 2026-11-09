"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { can, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { revokeAllSessions } from "@/lib/session";
import { normalizeMobile } from "@/lib/ids";
import { otpChannel } from "@/lib/env";
import { isLocked, isPermissionKey, PERMISSION_KEYS, roleDefault, STAFF_ROLES, type Role } from "@/lib/permissions";
import type { AppUser } from "@/lib/types";

export type ActionState = { ok: boolean; message: string | null; at: number };

async function admin() {
  const viewer = await staffForApi();
  return viewer && can(viewer, "admin.access") ? viewer : null;
}

const done = (message: string): ActionState => ({ ok: true, message, at: Date.now() });
const failed = (message: string): ActionState => ({ ok: false, message, at: Date.now() });

/**
 * Saves the role matrix. The form sends the wanted value of every unlocked
 * cell; only differences from the default are stored.
 */
export async function saveRoleMatrix(cells: { role: Role; key: string; allowed: boolean }[]): Promise<ActionState> {
  const viewer = await admin();
  if (!viewer) return failed("Only Admin can change access.");
  const db = adminClient();
  const { data: before } = await db.from("role_permissions").select("role, key, allowed");
  const old = new Map(((before ?? []) as { role: Role; key: string; allowed: boolean }[]).map((r) => [`${r.role}:${r.key}`, r.allowed]));
  const changes: string[] = [];
  for (const c of cells) {
    if (!STAFF_ROLES.includes(c.role as (typeof STAFF_ROLES)[number]) || !isPermissionKey(c.key) || isLocked(c.role, c.key)) continue;
    const def = roleDefault(c.role, c.key);
    const was = old.get(`${c.role}:${c.key}`) ?? def;
    if (was === c.allowed) continue;
    changes.push(`${c.role} ${c.key}: ${was ? "on" : "off"} → ${c.allowed ? "on" : "off"}`);
    if (c.allowed === def) {
      await db.from("role_permissions").delete().eq("role", c.role).eq("key", c.key);
    } else {
      await db
        .from("role_permissions")
        .upsert({ role: c.role, key: c.key, allowed: c.allowed, updated_by: viewer.user.id, updated_at: new Date().toISOString() });
    }
  }
  if (!changes.length) return done("Nothing changed.");
  await logActivity(viewer, "access.role", { type: "permissions" }, { changes });
  revalidatePath("/", "layout");
  return done(`Saved ${changes.length} ${changes.length === 1 ? "change" : "changes"}.`);
}

export async function resetRoleMatrix(): Promise<ActionState> {
  const viewer = await admin();
  if (!viewer) return failed("Only Admin can change access.");
  const db = adminClient();
  const { data } = await db.from("role_permissions").select("role, key, allowed");
  await db.from("role_permissions").delete().neq("key", "");
  await logActivity(viewer, "access.reset", { type: "permissions" }, { removed: data ?? [] });
  revalidatePath("/", "layout");
  return done("All roles are back to the default access.");
}

/** Per-person access: each key is "default", "allow" or "deny". */
export async function savePersonAccess(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const userId = String(formData.get("user_id") ?? "");
  const db = adminClient();
  const { data: person } = await db.from("users").select("*").eq("id", userId).maybeSingle<AppUser>();
  if (!person || person.role === "parent" || person.role === "admin") return;
  const { data: before } = await db.from("user_permissions").select("key, allowed").eq("user_id", userId);
  const old = new Map(((before ?? []) as { key: string; allowed: boolean }[]).map((r) => [r.key, r.allowed]));
  const changes: string[] = [];
  for (const key of PERMISSION_KEYS) {
    if (isLocked(person.role, key)) continue;
    const v = String(formData.get(key) ?? "default");
    const want = v === "allow" ? true : v === "deny" ? false : undefined;
    const was = old.get(key);
    if (want === was) continue;
    changes.push(`${key}: ${label(was)} → ${label(want)}`);
    if (want === undefined) await db.from("user_permissions").delete().eq("user_id", userId).eq("key", key);
    else
      await db
        .from("user_permissions")
        .upsert({ user_id: userId, key, allowed: want, updated_by: viewer.user.id, updated_at: new Date().toISOString() });
  }
  if (changes.length) {
    await logActivity(viewer, "access.person", { type: "user", id: userId }, { person: `${person.staff_id} ${person.name}`, changes });
  }
  revalidatePath("/admin/access");
}

function label(v: boolean | undefined): string {
  return v === undefined ? "role default" : v ? "allow" : "deny";
}

export async function setSuspended(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const userId = String(formData.get("user_id") ?? "");
  const suspend = formData.get("suspend") === "1";
  if (userId === viewer.user.id) return; // Admin cannot suspend themselves.
  const db = adminClient();
  const { data: person } = await db
    .from("users")
    .update({ status: suspend ? "suspended" : "active" })
    .eq("id", userId)
    .select("staff_id, name, role")
    .maybeSingle<{ staff_id: string | null; name: string; role: Role }>();
  if (!person) return;
  if (suspend) await revokeAllSessions(userId);
  await logActivity(viewer, suspend ? "staff.suspend" : "staff.restore", { type: "user", id: userId }, { person: `${person.staff_id ?? person.role} ${person.name}` });
  revalidatePath("/admin/access");
}

export async function logoutEverywhere(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const userId = String(formData.get("user_id") ?? "");
  const { data: person } = await adminClient().from("users").select("staff_id, name, role").eq("id", userId).maybeSingle<{ staff_id: string | null; name: string; role: Role }>();
  if (!person) return;
  await revokeAllSessions(userId);
  await logActivity(viewer, "staff.logout_all", { type: "user", id: userId }, { person: `${person.staff_id ?? person.role} ${person.name}` });
  revalidatePath("/admin/access");
}

const NewStaff = z.object({
  role: z.enum(["admin", "management", "reception", "faculty"]),
  name: z.string().trim().min(2).max(80),
  mobile: z.string(),
  email: z.union([z.literal(""), z.string().trim().email()]),
});

export async function addStaff(_prev: ActionState, formData: FormData): Promise<ActionState> {
  const viewer = await admin();
  if (!viewer) return failed("Only Admin can add staff.");
  const parsed = NewStaff.safeParse({
    role: formData.get("role"),
    name: formData.get("name"),
    mobile: String(formData.get("mobile") ?? ""),
    email: String(formData.get("email") ?? "").trim(),
  });
  if (!parsed.success) return failed("Fill the role, a name and a valid email.");
  if (otpChannel() === "email" && !parsed.data.email) return failed("Add their email: the login code is sent there.");
  const mobile = normalizeMobile(parsed.data.mobile);
  if (!mobile) return failed("Enter a 10 digit Indian mobile number.");
  const db = adminClient();
  const { data: clash } = await db.from("users").select("staff_id").eq("mobile", mobile).neq("role", "parent").maybeSingle<{ staff_id: string }>();
  if (clash) return failed(`This mobile already belongs to ${clash.staff_id}.`);
  // Two admins adding at once could pick the same ID: try again once.
  for (let attempt = 0; attempt < 2; attempt++) {
    const { data: staffId } = await db.rpc("next_staff_id", { p_role: parsed.data.role });
    const { data, error } = await db
      .from("users")
      .insert({ staff_id: staffId, role: parsed.data.role, name: parsed.data.name, mobile, email: parsed.data.email || null })
      .select("id, staff_id")
      .single<{ id: string; staff_id: string }>();
    if (!error && data) {
      await logActivity(viewer, "staff.add", { type: "user", id: data.id }, { staff_id: data.staff_id, name: parsed.data.name, role: parsed.data.role });
      revalidatePath("/admin/access");
      return done(`Added ${data.staff_id} ${parsed.data.name}. They log in with ${data.staff_id} or their mobile; the code goes to ${otpChannel() === "email" ? "their email" : "their mobile"}.`);
    }
  }
  return failed("Could not add this person. Please try again.");
}

const Contact = z.object({
  user_id: z.string().uuid(),
  name: z.string().trim().min(2).max(80),
  mobile: z.string(),
  email: z.union([z.literal(""), z.string().trim().email()]),
});

/** Change a staff member's name, mobile or email (the login code goes to the email). */
export async function updateStaffContact(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const parsed = Contact.safeParse({
    user_id: formData.get("user_id"),
    name: formData.get("name"),
    mobile: String(formData.get("mobile") ?? ""),
    email: String(formData.get("email") ?? "").trim().toLowerCase(),
  });
  if (!parsed.success) return;
  const mobile = normalizeMobile(parsed.data.mobile);
  if (!mobile) return;
  const db = adminClient();
  const { data: person } = await db.from("users").select("*").eq("id", parsed.data.user_id).maybeSingle<AppUser>();
  if (!person || person.role === "parent") return;
  const { data: clash } = await db.from("users").select("id").eq("mobile", mobile).neq("role", "parent").neq("id", person.id).maybeSingle();
  if (clash) return;
  const next = { name: parsed.data.name, mobile, email: parsed.data.email || null };
  const changes = (Object.keys(next) as (keyof typeof next)[]).filter((k) => (person[k] ?? null) !== next[k]);
  if (!changes.length) return;
  await db.from("users").update(next).eq("id", person.id);
  await logActivity(viewer, "staff.edit", { type: "user", id: person.id }, {
    person: `${person.staff_id} ${person.name}`,
    changes: changes.map((k) => `${k}: ${person[k] ?? "—"} → ${next[k] ?? "—"}`),
  });
  revalidatePath("/admin/access");
}
