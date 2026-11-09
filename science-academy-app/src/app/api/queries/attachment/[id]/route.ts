import { NextResponse, type NextRequest } from "next/server";
import { can, canSeeStudent, getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { signedUrl } from "@/lib/storage";

/** Opens a file sent in a parent query: the parent of that thread, or staff who answer queries. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const db = adminClient();
  const { data: msg } = await db.from("query_messages").select("thread_id, attachment_path").eq("id", id).maybeSingle<{ thread_id: string; attachment_path: string | null }>();
  if (!msg?.attachment_path) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const { data: thread } = await db.from("query_threads").select("parent_user_id, student_id").eq("id", msg.thread_id).maybeSingle<{ parent_user_id: string; student_id: string }>();
  if (!thread) return NextResponse.json({ error: "Not found" }, { status: 404 });
  let allowed = viewer.user.role === "parent" ? thread.parent_user_id === viewer.user.id : can(viewer, "queries.reply");
  if (allowed && viewer.user.role !== "parent") {
    const { data: s } = await db.from("students").select("batch_id").eq("id", thread.student_id).maybeSingle();
    allowed = Boolean(s && canSeeStudent(viewer, s));
  }
  if (!allowed) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const url = await signedUrl("attachments", msg.attachment_path, 120);
  return url ? NextResponse.redirect(url) : NextResponse.json({ error: "File missing" }, { status: 404 });
}
