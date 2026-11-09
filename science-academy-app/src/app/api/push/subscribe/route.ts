import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import { getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";

const Sub = z.object({
  endpoint: z.string().url().max(1000),
  keys: z.object({ p256dh: z.string().min(10).max(300), auth: z.string().min(5).max(100) }),
});

/** Saves this phone for phone notifications (POST) or forgets it (DELETE). */
export async function POST(req: NextRequest) {
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  const parsed = Sub.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Bad subscription" }, { status: 400 });
  const { error } = await adminClient()
    .from("push_subscriptions")
    .upsert(
      {
        user_id: viewer.user.id,
        endpoint: parsed.data.endpoint,
        p256dh: parsed.data.keys.p256dh,
        auth: parsed.data.keys.auth,
        user_agent: req.headers.get("user-agent")?.slice(0, 200) ?? null,
      },
      { onConflict: "endpoint" },
    );
  if (error) return NextResponse.json({ error: "Could not save" }, { status: 500 });
  return NextResponse.json({ ok: true });
}

export async function DELETE(req: NextRequest) {
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  const body = (await req.json().catch(() => null)) as { endpoint?: string } | null;
  if (body?.endpoint) await adminClient().from("push_subscriptions").delete().eq("endpoint", body.endpoint).eq("user_id", viewer.user.id);
  return NextResponse.json({ ok: true });
}
