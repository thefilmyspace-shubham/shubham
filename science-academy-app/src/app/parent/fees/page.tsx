import { Download, IndianRupee, ReceiptText } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { normalizeInvoice, qrDataUrl } from "@/lib/fees-data";
import { upiLink } from "@/lib/billing-calc";
import { academyDetails, upiIsPlaceholder } from "@/lib/env";
import { balanceOf, dueDate, feeStatus, FEE_STATUS_LABEL } from "@/lib/fees";
import { dateLabel, monthLabel, monthStart, rupees, todayIst } from "@/lib/format";
import { ChildStrip } from "@/components/ChildStrip";
import { Card, Empty, Section } from "@/components/ui";
import { FeeStatusChip } from "@/app/(staff)/fees/StatusChip";
import type { Invoice } from "@/lib/types";

export const metadata = { title: "Fees" };

/** Parent Fees tab: own child only. */
export default async function ParentFeesPage({ searchParams }: { searchParams: Promise<{ child?: string }> }) {
  const { child: childParam } = await searchParams;
  const { children, child } = await parentContext(childParam);
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty icon={IndianRupee}>No student is linked to this login number. Please contact the academy.</Empty>
      </div>
    );
  }
  const today = todayIst();
  const current = monthStart(today);
  const db = adminClient();
  const [{ data: ledgerRows }, { data: bills }] = await Promise.all([
    db.from("fees_ledger").select("*").eq("student_id", child.id).lte("month", current).order("month", { ascending: false }),
    db.from("invoices").select("*").eq("student_id", child.id).eq("status", "issued").order("created_at", { ascending: false }).limit(50),
  ]);
  const ledger = ((ledgerRows ?? []) as { id: string; month: string; amount: number; paid: number }[]).map((r) => ({
    ...r,
    amount: Number(r.amount),
    paid: Number(r.paid),
  }));
  const receipts = ((bills ?? []) as Invoice[]).map(normalizeInvoice);

  // This month (the row may not exist yet early in the month).
  const thisRow = ledger.find((r) => r.month === current) ?? (Number(child.monthly_fee) > 0 ? { id: "new", month: current, amount: Number(child.monthly_fee), paid: 0 } : null);
  const earlier = ledger.filter((r) => r.month < current && balanceOf(r) > 0);
  const earlierDue = earlier.reduce((s, r) => s + balanceOf(r), 0);
  const status = thisRow ? feeStatus(thisRow.amount, thisRow.paid, thisRow.month, today) : null;

  const academy = academyDetails();
  const qr = upiIsPlaceholder(academy.upiId) ? null : await qrDataUrl(upiLink(academy.upiId, thisRow ? balanceOf(thisRow) + earlierDue : undefined, child.code ?? undefined));

  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent/fees" />
      <div className="mx-auto max-w-lg px-4">
        {thisRow && status ? (
          <Card className="mt-4 p-4">
            <div className="flex items-center justify-between">
              <p className="font-bold text-navy">{monthLabel(thisRow.month)}</p>
              <FeeStatusChip status={status} />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-field bg-field p-2">
                <p className="text-[11px] font-semibold text-muted">Fee</p>
                <p className="font-extrabold">{rupees(thisRow.amount)}</p>
              </div>
              <div className="rounded-field bg-ok-soft p-2">
                <p className="text-[11px] font-semibold text-muted">Paid</p>
                <p className="font-extrabold text-ok">{rupees(thisRow.paid)}</p>
              </div>
              <div className={`rounded-field p-2 ${balanceOf(thisRow) > 0 ? "bg-warn-soft" : "bg-field"}`}>
                <p className="text-[11px] font-semibold text-muted">Balance</p>
                <p className={`font-extrabold ${balanceOf(thisRow) > 0 ? "text-warn" : ""}`}>{rupees(balanceOf(thisRow))}</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted">
              Due date: <span className="font-semibold text-fg">{dateLabel(dueDate(thisRow.month))}</span>
              {status === "overdue" && <span className="font-semibold text-danger"> · {FEE_STATUS_LABEL.overdue}</span>}
            </p>
          </Card>
        ) : (
          <Card className="mt-4 p-4 text-sm text-muted">No fee is set for this month.</Card>
        )}

        {earlier.length > 0 && (
          <Section title={`Earlier months pending · ${rupees(earlierDue)}`}>
            <Card className="divide-y divide-line">
              {earlier.map((r) => (
                <div key={r.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <span className="font-semibold">{monthLabel(r.month)}</span>
                  <span className="font-bold text-danger">{rupees(balanceOf(r))}</span>
                </div>
              ))}
            </Card>
          </Section>
        )}

        <Section title="Receipts">
          {receipts.length === 0 ? (
            <Empty icon={ReceiptText}>No receipts yet.</Empty>
          ) : (
            <Card className="divide-y divide-line overflow-hidden">
              {receipts.map((b) => (
                <a key={b.id} href={`/api/bills/${b.id}/pdf`} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
                  <div className="min-w-0 flex-1">
                    <p className="font-bold text-navy">{b.number}</p>
                    <p className="text-xs text-muted">
                      {monthLabel(b.month)} · paid {dateLabel(b.paid_on)}
                    </p>
                  </div>
                  <span className="font-bold">{rupees(b.received)}</span>
                  <Download size={17} className="text-primary" aria-label="Download PDF" />
                </a>
              ))}
            </Card>
          )}
        </Section>

        <Section title="How to pay">
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1 text-sm">
                <p>
                  <span className="text-muted">UPI ID: </span>
                  <span className="font-bold">{academy.upiId}</span>
                </p>
                <p>
                  <span className="text-muted">Bank: </span>
                  <span className="font-semibold">{academy.bankName}</span>
                </p>
                <p>
                  <span className="text-muted">Account name: </span>
                  <span className="font-semibold">{academy.accountName}</span>
                </p>
                <p>
                  <span className="text-muted">Account no.: </span>
                  <span className="font-semibold">{academy.accountNumber}</span>
                </p>
                <p>
                  <span className="text-muted">IFSC: </span>
                  <span className="font-semibold">{academy.ifsc}</span>
                </p>
              </div>
              {qr ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={qr} alt="UPI QR code" width={112} height={112} className="rounded-md border border-line p-1" />
              ) : (
                <div className="grid h-28 w-28 shrink-0 place-items-center rounded-md border-2 border-dashed border-faint text-center text-[11px] font-bold text-faint">[UPI QR CODE]</div>
              )}
            </div>
            <p className="mt-3 text-xs text-muted">
              After paying, please tell the academy office (with the UPI / bank reference). The receipt appears here once the office makes the bill. You can also pay in cash at the office.
            </p>
          </Card>
        </Section>
      </div>
    </>
  );
}
