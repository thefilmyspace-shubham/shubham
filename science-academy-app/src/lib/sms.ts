import "server-only";
import { isProduction } from "./env";

/**
 * Sends the login code by SMS through MSG91 (India: DLT registered sender and
 * an approved OTP template whose text contains ##otp##).
 * Without MSG91 keys, in development only, the code is printed in the server log.
 */
export async function sendOtpSms(mobile: string, code: string): Promise<{ ok: true; dev?: boolean } | { ok: false; error: string }> {
  const authKey = process.env.MSG91_AUTH_KEY;
  const templateId = process.env.MSG91_OTP_TEMPLATE_ID;
  if (!authKey || !templateId) {
    if (isProduction()) return { ok: false, error: "SMS is not set up yet. Please contact the academy." };
    console.info(`[dev] login code for ${mobile}: ${code}`);
    return { ok: true, dev: true };
  }
  try {
    const res = await fetch("https://control.msg91.com/api/v5/flow", {
      method: "POST",
      headers: { authkey: authKey, "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        short_url: "0",
        recipients: [{ mobiles: `91${mobile}`, otp: code }],
      }),
    });
    if (!res.ok) {
      console.error("msg91 failed", res.status, await res.text().catch(() => ""));
      return { ok: false, error: "Could not send the SMS. Please try again." };
    }
    return { ok: true };
  } catch (err) {
    console.error("msg91 failed", err);
    return { ok: false, error: "Could not send the SMS. Please try again." };
  }
}
