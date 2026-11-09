import Link from "next/link";
import { notFound } from "next/navigation";
import { Download, Mail, Plus } from "lucide-react";
import { can, canSeeBatch, requireStaff } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { getInvoice, qrDataUrl, staffNames } from "@/lib/fees-data";
import { upiLink } from "@/lib/billing-calc";
import { academyDetails, upiIsPlaceholder } from "@/lib/env";
import { dateTimeLabel } from "@/lib/format";
import { Banner, Page, PageHeader } from "@/components/ui";
import { ActionForm } from "../../fees/ActionForm";
import { emailBill } from "../actions";
import { Receipt } from "./Receipt";
import { CancelBill, PrintButton } from "./BillActions";

export const metadata = { title: "Bill" };

export default async function BillPage({ params }: { params: Promise<{ id: string }> }) {
  const viewer = await requireStaff();
  if (!can(viewer, "bills.create") && !can(viewer, "fees.view")) notFound();
  const { id } = await params;
  const inv = await getInvoice(id);
  if (!inv) notFound();
  const { data: student } = await adminClient().from("students").select("email, batch_id").eq("id", inv.student_id).maybeSingle();
  if (!student || !canSeeBatch(viewer, student.batch_id)) notFound();

  const academy = academyDetails();
  const qr = upiIsPlaceholder(academy.upiId) ? null : await qrDataUrl(upiLink(academy.upiId));
  const names = await staffNames([inv.created_by, inv.cancelled_by]);
  const canBill = can(viewer, "bills.create");

  return (
    <>
      <PageHeader title={inv.number} subtitle={`${inv.student_name} · ${inv.student_code}`} back="/billing" />
      <Page wide>
        <div className="no-print mb-4 space-y-3">
          {inv.status === "cancelled" && (
            <Banner tone="danger">
              Cancelled by {names.get(inv.cancelled_by ?? "") ?? "Admin"} on {dateTimeLabel(inv.cancelled_at ?? inv.created_at)}. Reason: {inv.cancelled_reason}
            </Banner>
          )}
          <div className="flex flex-wrap items-start gap-2">
            <a href={`/api/bills/${inv.id}/pdf`} className="btn btn-primary">
              <Download size={16} /> Save PDF
            </a>
            <PrintButton id={inv.id} />
            {canBill && inv.status === "issued" && (
              <ActionForm
                action={emailBill}
                fields={{ id: inv.id }}
                label={student.email ? `Email to parent` : "Email to parent (no email)"}
                icon={<Mail size={16} />}
                className="btn btn-ghost"
              />
            )}
            {canBill && (
              <Link href={`/billing/new?student=${inv.student_id}`} className="btn btn-soft">
                <Plus size={16} /> Another bill
              </Link>
            )}
            <Link href={`/fees/${inv.student_id}`} className="btn btn-ghost">
              Student fees
            </Link>
          </div>
          <p className="text-xs text-muted">
            Made by {names.get(inv.created_by) ?? "staff"} on {dateTimeLabel(inv.created_at)}
            {inv.emailed_at ? ` · emailed ${dateTimeLabel(inv.emailed_at)}` : ""}
            {student.email ? ` · parent email ${student.email}` : ""}
          </p>
          {can(viewer, "bills.cancel") && inv.status === "issued" && <CancelBill id={inv.id} number={inv.number} />}
        </div>

        {/* On screen: one copy. Printing: office copy and parent copy on separate pages. */}
        <div className="print-page">
          <Receipt inv={inv} academy={academy} qr={qr} copy="Office copy" />
        </div>
        <div className="print-page hidden print:block">
          <Receipt inv={inv} academy={academy} qr={qr} copy="Parent copy" />
        </div>
      </Page>
    </>
  );
}
