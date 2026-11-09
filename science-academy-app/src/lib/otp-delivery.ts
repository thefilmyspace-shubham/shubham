import "server-only";
import { adminClient } from "./supabase/admin";
import { isProduction, otpChannel } from "./env";
import { mailIsSetUp, maskEmail, sendMail } from "./mailer";
import { sendOtpSms } from "./sms";
import { OTP_TTL_MINUTES } from "./otp-rules";
import type { AppUser } from "./types";
import { asLang, translator, type TFn } from "./i18n";

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

/**
 * Sends the code by the configured channel (email by default). `t` is the
 * login screen's language (for errors); the email itself is written in the
 * person's own language.
 */
export async function deliverLoginCode(user: AppUser, code: string, t: TFn = translator("en")): Promise<Delivery> {
  if (otpChannel() === "sms") {
    const sms = await sendOtpSms(user.mobile, code);
    if (sms.ok) return { ok: true, sentTo: `+91 ${user.mobile.slice(0, 2)}•••••${user.mobile.slice(-3)}`, dev: sms.dev };
    return { ok: false, error: process.env.MSG91_AUTH_KEY ? t("core.otp.smsFailed") : t("core.otp.smsNotSetUp") };
  }
  const emails = await loginEmailsFor(user);
  if (!emails.length) {
    return { ok: false, error: user.role === "parent" ? t("core.otp.noEmailParent") : t("core.otp.noEmailStaff") };
  }
  const m = translator(asLang(user.language));
  const valid = m("core.otp.emailValid", { min: OTP_TTL_MINUTES });
  const mail = await sendMail({
    to: emails,
    subject: m("core.otp.emailSubject", { code }),
    text: `${m("core.otp.emailCodeIs")} ${code}.\n${valid}\n\n${m("core.otp.emailIgnore")}\n\nScience Academy, Ratlam`,
    html: `<div style="font-family:Arial,sans-serif;font-size:15px;color:#131a2a">
<p>${m("core.otp.emailCodeIs")}</p>
<p style="font-size:30px;font-weight:bold;letter-spacing:6px;color:#0b3c5d;margin:12px 0">${code}</p>
<p>${valid}</p>
<p style="color:#5f6b7d;font-size:13px">${m("core.otp.emailIgnore")}<br>Science Academy, Ratlam</p></div>`,
  });
  if (mail.ok) return { ok: true, sentTo: emails.map(maskEmail).join(", "), dev: mail.dev };
  return { ok: false, error: !mailIsSetUp() && isProduction() ? t("core.otp.emailNotSetUp") : t("core.otp.emailFailed") };
}
