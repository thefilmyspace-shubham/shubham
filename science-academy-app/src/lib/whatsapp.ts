import "server-only";

/**
 * WhatsApp messages through Meta's WhatsApp Cloud API (business number +
 * an approved message template). Settings:
 *   WHATSAPP_TOKEN            permanent access token (System user)
 *   WHATSAPP_PHONE_NUMBER_ID  the academy number's id in WhatsApp Manager
 *   WHATSAPP_FEE_TEMPLATE     template name, e.g. fee_due_tomorrow
 *   WHATSAPP_TEMPLATE_LANG    template language code (default "en")
 * The fee template has three values: {{1}} student name, {{2}} amount, {{3}} due date.
 */
export function whatsappIsSetUp(): boolean {
  return Boolean(process.env.WHATSAPP_TOKEN && process.env.WHATSAPP_PHONE_NUMBER_ID && process.env.WHATSAPP_FEE_TEMPLATE);
}

export type WaResult = { ok: true; id: string | null } | { ok: false; error: string; skipped?: boolean };

export async function sendFeeTemplate(mobile: string, values: [string, string, string]): Promise<WaResult> {
  if (!whatsappIsSetUp()) return { ok: false, error: "WhatsApp is not set up", skipped: true };
  try {
    const base = process.env.WHATSAPP_API_URL || "https://graph.facebook.com/v21.0";
    const res = await fetch(`${base}/${process.env.WHATSAPP_PHONE_NUMBER_ID}/messages`, {
      method: "POST",
      headers: { authorization: `Bearer ${process.env.WHATSAPP_TOKEN}`, "content-type": "application/json" },
      body: JSON.stringify({
        messaging_product: "whatsapp",
        to: `91${mobile}`,
        type: "template",
        template: {
          name: process.env.WHATSAPP_FEE_TEMPLATE,
          language: { code: process.env.WHATSAPP_TEMPLATE_LANG || "en" },
          components: [{ type: "body", parameters: values.map((text) => ({ type: "text", text })) }],
        },
      }),
    });
    const data = (await res.json().catch(() => null)) as { messages?: { id: string }[]; error?: { message?: string } } | null;
    if (!res.ok) return { ok: false, error: data?.error?.message ?? `WhatsApp error ${res.status}` };
    return { ok: true, id: data?.messages?.[0]?.id ?? null };
  } catch (err) {
    return { ok: false, error: String(err).slice(0, 200) };
  }
}
