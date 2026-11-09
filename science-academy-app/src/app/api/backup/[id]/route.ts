import { NextResponse, type NextRequest } from "next/server";
import { can, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { readFile } from "@/lib/storage";
import { logActivity } from "@/lib/activity";

/** Download one backup .xlsx (Admin only). Every download is logged. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "admin.backup")) return NextResponse.json({ error: "Not allowed" }, { status: 403 });
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const { data } = await adminClient().from("backups").select("file_path, rows_total, created_at").eq("id", id).maybeSingle<{ file_path: string; rows_total: number; created_at: string }>();
  if (!data) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const file = await readFile("backups", data.file_path);
  if (!file) return NextResponse.json({ error: "File missing" }, { status: 404 });
  await logActivity(viewer, "export.backup", { type: "backup", id }, { file: data.file_path.split("/").pop(), rows: data.rows_total });
  const name = data.file_path.split("/").pop()?.replace(/^[0-9a-f-]{36}-/, "") ?? "backup.xlsx";
  return new NextResponse(new Uint8Array(file), {
    headers: {
      "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "content-disposition": `attachment; filename="${name}"`,
      "cache-control": "no-store",
    },
  });
}
