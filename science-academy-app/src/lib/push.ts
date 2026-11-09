import "server-only";
import webpush from "web-push";
import { adminClient } from "./supabase/admin";

// Phone notifications (web push). The VAPID key pair is made by the app the
// first time it is needed and kept in app_secrets (server only), so nothing
// has to be set up in Vercel.

let keys: { publicKey: string; privateKey: string } | null = null;

export async function vapidKeys(): Promise<{ publicKey: string; privateKey: string } | null> {
  if (keys) return keys;
  const db = adminClient();
  const read = async () => {
    const { data, error } = await db.from("app_secrets").select("key, value").in("key", ["vapid_public", "vapid_private"]);
    if (error) return null; // migration not run yet
    const map = new Map(((data ?? []) as { key: string; value: string }[]).map((r) => [r.key, r.value]));
    return map.get("vapid_public") && map.get("vapid_private") ? { publicKey: map.get("vapid_public")!, privateKey: map.get("vapid_private")! } : null;
  };
  let found = await read();
  if (!found) {
    const made = webpush.generateVAPIDKeys();
    // Two servers at once: the first one wins, both read back the same pair.
    await db.from("app_secrets").upsert(
      [
        { key: "vapid_public", value: made.publicKey },
        { key: "vapid_private", value: made.privateKey },
      ],
      { onConflict: "key", ignoreDuplicates: true },
    );
    found = await read();
  }
  if (found) keys = found;
  return found;
}

export type PushItem = { userId: string; title: string; body: string | null; link: string | null };

/** Sends phone notifications to every phone each person turned them on for. Never throws. */
export async function sendPush(items: PushItem[]): Promise<void> {
  if (!items.length) return;
  try {
    const k = await vapidKeys();
    if (!k) return;
    webpush.setVapidDetails("mailto:noreply@science-academy-app.vercel.app", k.publicKey, k.privateKey);
    const db = adminClient();
    const ids = [...new Set(items.map((i) => i.userId))];
    const { data } = await db.from("push_subscriptions").select("*").in("user_id", ids);
    const subs = (data ?? []) as { id: string; user_id: string; endpoint: string; p256dh: string; auth: string }[];
    if (!subs.length) return;
    const dead: string[] = [];
    await Promise.allSettled(
      items.flatMap((item) =>
        subs
          .filter((s) => s.user_id === item.userId)
          .map((s) =>
            webpush
              .sendNotification(
                { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
                JSON.stringify({ title: item.title, body: item.body ?? "", url: item.link ?? "/" }),
                { TTL: 60 * 60 * 24, timeout: 8000 },
              )
              .catch((err: { statusCode?: number }) => {
                if (err?.statusCode === 404 || err?.statusCode === 410) dead.push(s.id);
              }),
          ),
      ),
    );
    if (dead.length) await db.from("push_subscriptions").delete().in("id", dead);
  } catch (err) {
    console.error("push failed", err);
  }
}
