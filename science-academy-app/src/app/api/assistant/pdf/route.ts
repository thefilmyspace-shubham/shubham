import { NextResponse, type NextRequest } from "next/server";
import { can, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { drawFooters, drawHeader, drawTable, newDoc, pdfHeaders, toBuffer, PAGE_W, MARGIN, type Column } from "@/lib/pdf";
import { dateLabel, todayIst } from "@/lib/format";
import type { AiMessage } from "@/lib/assistant/chat";

/** PDF of a comparison table from one of the person's own assistant answers. */
export async function GET(req: NextRequest) {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "ai.ask")) return NextResponse.json({ error: "Not allowed" }, { status: 403 });
  const id = req.nextUrl.searchParams.get("message") ?? "";
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const { data } = await adminClient().from("ai_messages").select("*").eq("id", id).eq("user_id", viewer.user.id).maybeSingle<AiMessage>();
  const table = data?.attachment?.kind === "table" ? data.attachment : null;
  if (!table) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const doc = newDoc();
  const y = drawHeader(doc, {
    title: table.title,
    subtitle: `Made by ${viewer.user.staff_id} ${viewer.user.name} with the AI assistant`,
    right: ["Report", dateLabel(todayIst())],
  });
  const usable = PAGE_W - MARGIN * 2;
  const first = Math.min(70, usable * 0.4);
  const rest = table.columns.length > 1 ? (usable - first) / (table.columns.length - 1) : usable;
  const columns: Column[] = table.columns.map((c, i) => ({ header: c, width: i === 0 ? first : rest, align: i === 0 ? "left" : "right" }));
  drawTable(doc, columns, table.rows, y);
  drawFooters(doc);
  const name = `${table.title.slice(0, 60)}.pdf`;
  return new NextResponse(new Uint8Array(toBuffer(doc)), { headers: pdfHeaders(name) });
}
