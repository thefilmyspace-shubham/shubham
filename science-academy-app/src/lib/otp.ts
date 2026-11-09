import "server-only";
import { createHmac, randomInt, timingSafeEqual } from "node:crypto";
import { adminClient } from "./supabase/admin";
import { otpChannel, serviceRoleKey } from "./env";
import { normalizeMobile, parseStaffId } from "./ids";
import { ensureParentUser } from "./notify";
import type { Role } from "./permissions";
import type { AppUser } from "./types";

import { MAX_ATTEMPTS, MAX_SENDS_PER_HOUR, OTP_TTL_MINUTES, RESEND_AFTER_SECONDS } from "./otp-rules";
import { deliverLoginCode } from "./otp-delivery";

function hashCode(userId: string, code: string): string {
  return createHmac("sha256", serviceRoleKey()).update(`${userId}:${code}`).digest("hex");
}

/**
 * Who is logging in. Staff type their email, staff ID (AD-01) or registered
 * mobile; parents type their child's login number or the email given at
 * registration.
 */
export async function findLoginUser(role: Role, identifier: string): Promise<AppUser | null> {
  const db = adminClient();
  const email = parseEmail(identifier);
  if (role !== "parent") {
    const staffId = email ? null : parseStaffId(identifier);
    const mobile = email || staffId ? null : normalizeMobile(identifier);
    if (!email && !staffId && !mobile) return null;
    let q = db.from("users").select("*").eq("role", role);
    q = email ? q.ilike("email", likeExact(email)) : staffId ? q.eq("staff_id", staffId) : q.eq("mobile", mobile!);
    const { data } = await q.limit(1).maybeSingle<AppUser>();
    return data ?? null;
  }
  const mobile = email ? await loginNumberForEmail(email) : normalizeMobile(identifier);
  if (!mobile) return null;
  const { data } = await db.from("users").select("*").eq("role", "parent").eq("mobile", mobile).maybeSingle<AppUser>();
  if (data) return data;
  // A login number chosen at registration whose login row is missing: make it now.
  const { data: link } = await db
    .from("guardians")
    .select("name, students!inner(status)")
    .eq("mobile", mobile)
    .eq("is_login_number", true)
    .in("students.status", ["active", "passed_out"])
    .limit(1)
    .maybeSingle<{ name: string | null }>();
  return link ? ensureParentUser(mobile, link.name ?? "Parent") : null;
}

/** "Name@Gmail.com " → "name@gmail.com"; null when it is not an email. */
export function parseEmail(text: string): string | null {
  const t = text.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t) ? t : null;
}

/** An exact, case-insensitive match for ilike (escapes its wildcards). */
function likeExact(text: string): string {
  return text.replace(/[\\%_]/g, (c) => `\\${c}`);
}

/** The login number of the student registered with this parent email. */
async function loginNumberForEmail(email: string): Promise<string | null> {
  const db = adminClient();
  const { data: kids } = await db
    .from("students")
    .select("id")
    .ilike("email", likeExact(email))
    .in("status", ["active", "passed_out"])
    .limit(5);
  const ids = ((kids ?? []) as { id: string }[]).map((k) => k.id);
  if (!ids.length) return null;
  const { data: g } = await db
    .from("guardians")
    .select("mobile")
    .in("student_id", ids)
    .eq("is_login_number", true)
    .limit(1)
    .maybeSingle<{ mobile: string }>();
  return g?.mobile ?? null;
}

export type SendResult =
  | { ok: true; challenge: string; sentTo: string; channel: "email" | "sms"; devCode?: string }
  | { ok: false; error: string; retryAfter?: number };

export async function sendLoginCode(user: AppUser, now = new Date()): Promise<SendResult> {
  if (user.status !== "active") return { ok: false, error: "This login is suspended. Please contact the academy." };
  const db = adminClient();
  const hourAgo = new Date(now.getTime() - 3600_000).toISOString();
  const { data: recent } = await db
    .from("otp_codes")
    .select("created_at")
    .eq("user_id", user.id)
    .gte("created_at", hourAgo)
    .order("created_at", { ascending: false });
  const sends = (recent ?? []) as { created_at: string }[];
  if (sends.length) {
    const since = (now.getTime() - Date.parse(sends[0].created_at)) / 1000;
    if (since < RESEND_AFTER_SECONDS) {
      return { ok: false, error: "Please wait before asking for a new code.", retryAfter: Math.ceil(RESEND_AFTER_SECONDS - since) };
    }
  }
  if (sends.length >= MAX_SENDS_PER_HOUR) return { ok: false, error: "Too many codes asked. Please try again in an hour." };

  const code = String(randomInt(0, 1_000_000)).padStart(6, "0");
  const { data: row, error } = await db
    .from("otp_codes")
    .insert({
      user_id: user.id,
      code_hash: hashCode(user.id, code),
      expires_at: new Date(now.getTime() + OTP_TTL_MINUTES * 60_000).toISOString(),
    })
    .select("id")
    .single<{ id: string }>();
  if (error || !row) return { ok: false, error: "Could not make a code. Please try again." };

  const sent = await deliverLoginCode(user, code);
  if (!sent.ok) {
    // Not delivered: drop the code so it does not hold up a retry.
    await db.from("otp_codes").delete().eq("id", row.id);
    return { ok: false, error: sent.error };
  }
  return {
    ok: true,
    challenge: row.id,
    sentTo: sent.sentTo,
    channel: otpChannel(),
    ...(sent.dev ? { devCode: code } : {}),
  };
}

export type VerifyResult = { ok: true; user: AppUser } | { ok: false; error: string };

/** Checks a code against the challenge it was sent for. A code works once. */
export async function verifyLoginCode(challenge: string, code: string, now = new Date()): Promise<VerifyResult> {
  if (!/^\d{6}$/.test(code)) return { ok: false, error: "Enter the 6 digit code." };
  if (!/^[0-9a-f-]{36}$/i.test(challenge)) return { ok: false, error: "Please ask for a new code." };
  const db = adminClient();
  const { data: row } = await db
    .from("otp_codes")
    .select("id, user_id, code_hash, expires_at, attempts, consumed_at")
    .eq("id", challenge)
    .maybeSingle<{ id: string; user_id: string; code_hash: string; expires_at: string; attempts: number; consumed_at: string | null }>();
  if (!row || row.consumed_at) return { ok: false, error: "This code was already used. Please ask for a new one." };
  if (Date.parse(row.expires_at) < now.getTime()) return { ok: false, error: "This code has expired. Please ask for a new one." };
  if (row.attempts >= MAX_ATTEMPTS) return { ok: false, error: "Too many wrong tries. Please ask for a new code." };

  const expected = Buffer.from(row.code_hash, "hex");
  const given = Buffer.from(hashCode(row.user_id, code), "hex");
  if (expected.length !== given.length || !timingSafeEqual(expected, given)) {
    await db.from("otp_codes").update({ attempts: row.attempts + 1 }).eq("id", row.id);
    const left = MAX_ATTEMPTS - row.attempts - 1;
    return { ok: false, error: left > 0 ? `Wrong code. ${left} ${left === 1 ? "try" : "tries"} left.` : "Too many wrong tries. Please ask for a new code." };
  }
  // Consume once (a second request with the same code loses the race).
  const { data: consumed } = await db
    .from("otp_codes")
    .update({ consumed_at: now.toISOString() })
    .eq("id", row.id)
    .is("consumed_at", null)
    .select("id");
  if (!consumed?.length) return { ok: false, error: "This code was already used. Please ask for a new one." };

  const { data: user } = await db.from("users").select("*").eq("id", row.user_id).maybeSingle<AppUser>();
  if (!user || user.status !== "active") return { ok: false, error: "This login is suspended. Please contact the academy." };
  return { ok: true, user };
}
