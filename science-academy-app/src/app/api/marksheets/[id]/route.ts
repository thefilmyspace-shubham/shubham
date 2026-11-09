import { NextResponse, type NextRequest } from "next/server";
import { can, canSeeStudent, childrenOf, getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { signedUrl } from "@/lib/storage";
import type { Marksheet, Student } from "@/lib/types";

/**
 * Opens a marksheet file through a 60-second signed link, after checking the
 * viewer may see it: staff with "See marksheets" (Faculty: own batches), or
 * the parent of that child.
 */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const db = adminClient();
  const { data: ms } = await db.from("marksheets").select("*").eq("id", id).maybeSingle<Marksheet>();
  if (!ms?.file_path) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const { data: student } = await db.from("students").select("*").eq("id", ms.student_id).maybeSingle<Student>();
  if (!student) return NextResponse.json({ error: "Not found" }, { status: 404 });

  let allowed = false;
  if (viewer.user.role === "parent") {
    allowed = (await childrenOf(viewer.user)).some((c) => c.id === student.id);
  } else {
    allowed = can(viewer, "students.marksheets") && canSeeStudent(viewer, student);
  }
  if (!allowed) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const url = await signedUrl("marksheets", ms.file_path, 60);
  if (!url) return NextResponse.json({ error: "File missing" }, { status: 404 });
  return NextResponse.redirect(url, { headers: { "cache-control": "no-store" } });
}
