import "server-only";
import { mailIsSetUp, sendMail } from "./mailer";

export type EmailResult = { ok: true } | { ok: false; error: string };

/**
 * Sends one email with attachments: through the academy's Gmail when
 * SMTP_USER / SMTP_PASSWORD are set (see mailer.ts), otherwise through Resend
 * (RESEND_API_KEY and BILL_FROM_EMAIL).
 */
export async function sendEmail(opts: {
  to: string;
  subject: string;
  html: string;
  attachments?: { filename: string; content: Buffer }[];
}): Promise<EmailResult> {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(opts.to)) return { ok: false, error: "The email address on the student's profile does not look right." };
  if (mailIsSetUp()) {
    const text = opts.html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    const r = await sendMail({ to: opts.to, subject: opts.subject, html: opts.html, text, attachments: opts.attachments });
    return r.ok ? { ok: true } : r;
  }
  const key = process.env.RESEND_API_KEY;
  const from = process.env.BILL_FROM_EMAIL;
  if (!key || !from) return { ok: false, error: "Email is not set up yet (academy Gmail: SMTP_USER and SMTP_PASSWORD). Use Save PDF or Print for now." };
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(opts.to)) return { ok: false, error: "The email address on the student's profile does not look right." };
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: JSON.stringify({
        from,
        to: [opts.to],
        subject: opts.subject,
        html: opts.html,
        attachments: (opts.attachments ?? []).map((a) => ({ filename: a.filename, content: a.content.toString("base64") })),
      }),
    });
    if (!res.ok) {
      console.error("resend failed", res.status, await res.text().catch(() => ""));
      return { ok: false, error: "The email could not be sent. Please try again." };
    }
    return { ok: true };
  } catch (err) {
    console.error("resend failed", err);
    return { ok: false, error: "The email could not be sent. Please try again." };
  }
}

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}
