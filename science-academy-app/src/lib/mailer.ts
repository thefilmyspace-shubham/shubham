import "server-only";
import nodemailer, { type Transporter } from "nodemailer";
import { isProduction } from "./env";

/**
 * Email through the academy's Gmail (SMTP with a Gmail App Password), the
 * same way the TFS app sends its login codes. Used for login codes and bills.
 *   SMTP_USER=academy@gmail.com  SMTP_PASSWORD=<16 letter app password>
 * Optional: SMTP_HOST (default smtp.gmail.com), SMTP_PORT (465), MAIL_FROM.
 */
let transport: Transporter | null = null;

export function mailIsSetUp(): boolean {
  return Boolean(process.env.SMTP_USER && process.env.SMTP_PASSWORD);
}

function transporter(): Transporter {
  if (!transport) {
    const port = Number(process.env.SMTP_PORT || 465);
    transport = nodemailer.createTransport({
      host: process.env.SMTP_HOST || "smtp.gmail.com",
      port,
      secure: port === 465,
      auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASSWORD },
    });
  }
  return transport;
}

export function fromAddress(): string {
  return process.env.MAIL_FROM || `Science Academy <${process.env.SMTP_USER}>`;
}

export type MailResult = { ok: true; dev?: boolean } | { ok: false; error: string };

export async function sendMail(opts: {
  to: string | string[];
  subject: string;
  text: string;
  html?: string;
  attachments?: { filename: string; content: Buffer }[];
}): Promise<MailResult> {
  if (!mailIsSetUp()) {
    if (isProduction()) return { ok: false, error: "Email is not set up yet. Please contact the academy." };
    console.info(`[dev] email to ${String(opts.to)}: ${opts.subject}\n${opts.text}`);
    return { ok: true, dev: true };
  }
  try {
    await transporter().sendMail({ from: fromAddress(), ...opts });
    return { ok: true };
  } catch (err) {
    console.error("email failed", err);
    return { ok: false, error: "The email could not be sent. Please try again." };
  }
}

/** s••••a@gmail.com */
export function maskEmail(email: string): string {
  const [name, domain] = email.split("@");
  if (!domain) return "your email";
  const shown = name.length <= 2 ? name.charAt(0) : `${name.charAt(0)}${"•".repeat(Math.min(name.length - 2, 5))}${name.slice(-1)}`;
  return `${shown}@${domain}`;
}
