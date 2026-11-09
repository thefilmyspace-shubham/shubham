import { NextResponse, type NextRequest } from "next/server";
import { can, canSeeBatch, childrenOf, getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { getInvoice } from "@/lib/fees-data";
import { billFileName, buildBillPdf } from "@/lib/bill-pdf";
import { pdfHeaders } from "@/lib/pdf";

/**
 * The bill as a PDF. Staff who make bills or see fees get both copies;
 * a parent gets the parent copy of their own child's issued receipts only.
 */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const viewer = await getViewer();
  if (!viewer) return NextResponse.json({ error: "Login required" }, { status: 401 });
  const { id } = await params;
  const inv = await getInvoice(id);
  const missing = NextResponse.json({ error: "Bill not found" }, { status: 404 });
  if (!inv) return missing;

  if (viewer.user.role === "parent") {
    const children = await childrenOf(viewer.user);
    if (inv.status !== "issued" || !children.some((c) => c.id === inv.student_id)) return missing;
    const pdf = await buildBillPdf(inv, { copies: ["Parent copy"] });
    return new NextResponse(new Uint8Array(pdf), { headers: pdfHeaders(billFileName(inv)) });
  }

  if (!can(viewer, "bills.create") && !can(viewer, "fees.view")) return missing;
  const { data: student } = await adminClient().from("students").select("batch_id").eq("id", inv.student_id).maybeSingle();
  if (!student || !canSeeBatch(viewer, student.batch_id)) return missing;
  const pdf = await buildBillPdf(inv);
  return new NextResponse(new Uint8Array(pdf), { headers: pdfHeaders(billFileName(inv)) });
}
