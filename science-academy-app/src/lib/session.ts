import "server-only";
import { adminClient } from "./supabase/admin";
import { createClient } from "./supabase/server";
import type { AppUser } from "./types";

/**
 * Every app user has a hidden Supabase Auth account (never emailed). After the
 * SMS code is checked here, a one-time sign-in token for that account is made
 * and exchanged on the server, which sets the session cookies. The session
 * stays until Log out (the cookie lasts 400 days and refreshes itself).
 */
function authEmailFor(user: AppUser): string {
  return `u-${user.id}@login.science-academy.app`;
}

async function ensureAuthUser(user: AppUser): Promise<string> {
  const db = adminClient();
  if (user.auth_user_id) return authEmailFor(user);
  const email = authEmailFor(user);
  const { data, error } = await db.auth.admin.createUser({
    email,
    email_confirm: true,
    user_metadata: { app_user_id: user.id },
  });
  let authId = data?.user?.id;
  if (error || !authId) {
    // Made already (an earlier login that failed half way): find it.
    const { data: list } = await db.auth.admin.listUsers({ page: 1, perPage: 1000 });
    authId = list?.users.find((u) => u.email === email)?.id;
    if (!authId) throw new Error(`could not create login: ${error?.message}`);
  }
  await db.from("users").update({ auth_user_id: authId }).eq("id", user.id);
  return email;
}

function sessionIdOf(accessToken: string): string | null {
  try {
    const payload = JSON.parse(Buffer.from(accessToken.split(".")[1], "base64url").toString("utf8"));
    return typeof payload.session_id === "string" ? payload.session_id : null;
  } catch {
    return null;
  }
}

/** Signs the user in on this device (sets cookies) and records the session. */
export async function startSession(user: AppUser, userAgent: string | null): Promise<void> {
  const email = await ensureAuthUser(user);
  const db = adminClient();
  const { data: link, error } = await db.auth.admin.generateLink({ type: "magiclink", email });
  if (error || !link?.properties?.hashed_token) throw new Error(`could not start session: ${error?.message}`);

  const supabase = await createClient();
  const { data, error: verifyError } = await supabase.auth.verifyOtp({
    type: "magiclink",
    token_hash: link.properties.hashed_token,
  });
  const token = data?.session?.access_token;
  const sessionId = token ? sessionIdOf(token) : null;
  if (verifyError || !sessionId) throw new Error(`could not start session: ${verifyError?.message}`);

  await db.from("login_sessions").insert({
    session_id: sessionId,
    user_id: user.id,
    user_agent: userAgent?.slice(0, 200) ?? null,
  });
}

/** Log out on this device. */
export async function endSession(sessionId: string | null): Promise<void> {
  if (sessionId) {
    await adminClient().from("login_sessions").update({ revoked_at: new Date().toISOString() }).eq("session_id", sessionId);
  }
  const supabase = await createClient();
  await supabase.auth.signOut({ scope: "local" });
}

/** Log out everywhere (also used when a login is suspended). */
export async function revokeAllSessions(userId: string): Promise<void> {
  await adminClient()
    .from("login_sessions")
    .update({ revoked_at: new Date().toISOString() })
    .eq("user_id", userId)
    .is("revoked_at", null);
}
