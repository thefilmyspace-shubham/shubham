import "server-only";
import { adminClient } from "./supabase/admin";
import { otpChannel } from "./env";
import { maskEmail, sendMail } from "./mailer";
import { sendOtpSms } from "./sms";
import { OTP_TTL_MINUTES } from "./otp-rules";
import type { AppUser } from "./types";

/**
 * Where a person's login code goes by email: staff → their own email;
 * parent → the email saved on their child's registration (all children
 * on this login number, if they differ).
 */
export async function loginEmailsFor(user: AppUser): Promise<string[]> {
  if (user.role !== "parent") return user.email ? [user.email.toLowerCase()] : [];
  const db = adminClient();
  const { data: links } = await db.from("guardians").select("student_id").eq("mobile", user.mobile).eq("is_login_number", true);
  const ids = ((links ?? []) as { student_id: string }[]).map((l) => l.student_id);
  if (!ids.length) return [];
  const { data } = await db.from("students").select("email").in("id", ids).in("status", ["active", "passed_out"]);
  const emails = ((data ?? []) as { email: string | null }[]).map((s) => s.email?.toLowerCase()).filter((e): e is string => Boolean(e));
  return [...new Set(emails)].slice(0, 3);
}

export type Delivery = { ok: true; sentTo: string; dev?: boolean } | { ok: false; error: string };

/** Sends the code by the configured channel (email by default). */
export async function deliverLoginCode(user: AppUser, code: string): Promise<Delivery> {
  if (otpChannel() === "sms") {
    const sms = await sendOtpSms(user.mobile, code);
    return sms.ok ? { ok: true, sentTo: `+91 ${user.mobile.slice(0, 2)}•••••${user.mobile.slice(-3)}`, dev: sms.dev } : sms;
  }
  const emails = await loginEmailsFor(user);
  if (!emails.length) {
    return {
      ok: false,
      error:
        user.role === "parent"
          ? "No email is saved for your child yet. Please ask the academy office to add it."
          : "No email is saved for your login yet. Please ask the Admin to add it in Access control.",
    };
  }
  const mail = await sendMail({
    to: emails,
    subject: `${code} is your Science Academy login code`,
    text: `Your Science Academy login code is ${code}.\nIt is valid for ${OTP_TTL_MINUTES} minutes. Do not share it with anyone.\n\nIf you did not try to log in, you can ignore this email.\n\nScience Academy, Ratlam`,
    html: `<div style="font-family:Arial,sans-serif;font-size:15px;color:#131a2a">
<p>Your <b>Science Academy</b> login code is</p>
<p style="font-size:30px;font-weight:bold;letter-spacing:6px;color:#0b3c5d;margin:12px 0">${code}</p>
<p>It is valid for ${OTP_TTL_MINUTES} minutes. Do not share it with anyone.</p>
<p style="color:#5f6b7d;font-size:13px">If you did not try to log in, you can ignore this email.<br>Science Academy, Ratlam</p></div>`,
  });
  return mail.ok ? { ok: true, sentTo: emails.map(maskEmail).join(", "), dev: mail.dev } : mail;
}
