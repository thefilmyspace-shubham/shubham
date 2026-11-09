import "server-only";
import { cache } from "react";
import { notFound, redirect } from "next/navigation";
import { createClient } from "./supabase/server";
import { adminClient } from "./supabase/admin";
import { resolvePermissions, type Overrides, type PermissionKey } from "./permissions";
import type { AppUser, Student } from "./types";

export type Viewer = {
  user: AppUser;
  sessionId: string;
  perms: Record<PermissionKey, boolean>;
  /** Faculty: the batches they teach. Everyone else on staff: null (no batch limit). */
  ownBatchIds: string[] | null;
};

export type StaffViewer = Viewer & { user: AppUser & { staff_id: string } };

/**
 * The signed-in person. The Supabase session must belong to an active app
 * user and must not have been revoked (Log out, Log out everywhere, Suspend).
 */
export const getViewer = cache(async (): Promise<Viewer | null> => {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const claims = data?.claims;
  if (!claims?.sub || typeof claims.session_id !== "string") return null;

  const db = adminClient();
  const { data: user } = await db
    .from("users")
    .select("*")
    .eq("auth_user_id", claims.sub)
    .eq("status", "active")
    .maybeSingle<AppUser>();
  if (!user) return null;

  const [{ data: session }, { data: roleRows }, { data: userRows }, { data: batches }] = await Promise.all([
    db.from("login_sessions").select("revoked_at").eq("session_id", claims.session_id).eq("user_id", user.id).maybeSingle(),
    db.from("role_permissions").select("key, allowed").eq("role", user.role),
    db.from("user_permissions").select("key, allowed").eq("user_id", user.id),
    user.role === "faculty"
      ? db.from("faculty_batches").select("batch_id").eq("user_id", user.id)
      : Promise.resolve({ data: null }),
  ]);
  if (!session || session.revoked_at) return null;

  const toMap = (rows: { key: string; allowed: boolean }[] | null) =>
    Object.fromEntries((rows ?? []).map((r) => [r.key, r.allowed])) as Overrides;
  return {
    user,
    sessionId: claims.session_id,
    perms: resolvePermissions(user.role, toMap(roleRows), toMap(userRows)),
    ownBatchIds: user.role === "faculty" ? ((batches ?? []) as { batch_id: string }[]).map((b) => b.batch_id) : null,
  };
});

export function can(viewer: Viewer, key: PermissionKey): boolean {
  return viewer.perms[key] === true;
}

export function homeFor(viewer: Viewer | null): "/" | "/parent" | "/login" {
  if (!viewer) return "/login";
  return viewer.user.role === "parent" ? "/parent" : "/";
}

/** For staff pages: an active staff login, or a redirect. */
export async function requireStaff(): Promise<StaffViewer> {
  const viewer = await getViewer();
  if (!viewer) redirect("/login");
  if (viewer.user.role === "parent") redirect("/parent");
  return viewer as StaffViewer;
}

/** For a page that needs one permission: anyone without it gets a 404. */
export async function requirePermission(...keys: PermissionKey[]): Promise<StaffViewer> {
  const viewer = await requireStaff();
  if (!keys.every((k) => can(viewer, k))) notFound();
  return viewer;
}

/** For the parent app. */
export async function requireParent(): Promise<Viewer> {
  const viewer = await getViewer();
  if (!viewer) redirect("/login");
  if (viewer.user.role !== "parent") redirect("/");
  return viewer;
}

/** For API routes and server actions: the staff viewer, or null. */
export async function staffForApi(): Promise<StaffViewer | null> {
  const viewer = await getViewer();
  return viewer && viewer.user.role !== "parent" ? (viewer as StaffViewer) : null;
}

/** "AD-01 Shubham" */
export function actorLabel(user: AppUser): string {
  return user.staff_id ? `${user.staff_id} ${user.name}` : `Parent ${user.name}`;
}

/**
 * Batches this person may see students, attendance and scores of.
 * null = every batch.
 */
export function visibleBatchIds(viewer: Viewer): string[] | null {
  return viewer.user.role === "faculty" ? (viewer.ownBatchIds ?? []) : null;
}

export function canSeeBatch(viewer: Viewer, batchId: string | null): boolean {
  const ids = visibleBatchIds(viewer);
  return ids === null || (batchId !== null && ids.includes(batchId));
}

/** May this staff member open this student's profile? */
export function canSeeStudent(viewer: Viewer, student: Pick<Student, "batch_id">): boolean {
  return can(viewer, "students.view") && canSeeBatch(viewer, student.batch_id);
}

/** The children linked to a parent login (their one login number). */
export const childrenOf = cache(async (parent: AppUser): Promise<Student[]> => {
  const db = adminClient();
  const { data: links } = await db
    .from("guardians")
    .select("student_id")
    .eq("mobile", parent.mobile)
    .eq("is_login_number", true);
  const ids = ((links ?? []) as { student_id: string }[]).map((l) => l.student_id);
  if (!ids.length) return [];
  const { data } = await db
    .from("students")
    .select("*")
    .in("id", ids)
    .in("status", ["active", "passed_out"])
    .order("name");
  return (data ?? []) as Student[];
});
