import { NextResponse, type NextRequest } from "next/server";
import { getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { groupFor } from "@/lib/groups-db";
import { signedUrl } from "@/lib/storage";

/** Opens a chat attachment: only for someone who may read its group. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const { data: msg } = await adminClient()
    .from("messages")
    .select("group_id, attachment_path")
    .eq("id", id)
    .maybeSingle<{ group_id: string; attachment_path: string | null }>();
  if (!msg?.attachment_path) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const group = await groupFor(viewer, msg.group_id);
  if (!group) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const url = await signedUrl("attachments", msg.attachment_path, 120);
  if (!url) return NextResponse.json({ error: "File missing" }, { status: 404 });
  return NextResponse.redirect(url);
}
