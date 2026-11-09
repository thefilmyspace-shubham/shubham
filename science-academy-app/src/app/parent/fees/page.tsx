import { Download, IndianRupee, ReceiptText } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { normalizeInvoice, qrDataUrl } from "@/lib/fees-data";
import { upiLink } from "@/lib/billing-calc";
import { academyDetails, upiIsPlaceholder } from "@/lib/env";
import { balanceOf, feeStatus, rowDue, type FeePlan } from "@/lib/fees";
import { getT } from "@/lib/i18n/server";
import { dateLabel, monthLabel, monthStart, rupees, todayIst } from "@/lib/format";
import { ChildStrip } from "@/components/ChildStrip";
import { Card, Empty, Section } from "@/components/ui";
import { FeeStatusChip } from "@/app/(staff)/fees/StatusChip";
import type { Invoice } from "@/lib/types";

export const metadata = { title: "Fees" };

/** Parent Fees tab: own child only. */
export default async function ParentFeesPage({ searchParams }: { searchParams: Promise<{ child?: string }> }) {
  const { child: childParam } = await searchParams;
  const { t } = await getT();
  const { children, child } = await parentContext(childParam);
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty icon={IndianRupee}>{t("fees.p.noStudent")}</Empty>
      </div>
    );
  }
  const today = todayIst();
  const current = monthStart(today);
  const db = adminClient();
  const [{ data: ledgerRows }, { data: bills }] = await Promise.all([
    db.from("fees_ledger").select("*").eq("student_id", child.id).order("month", { ascending: false }),
    db.from("invoices").select("*").eq("student_id", child.id).eq("status", "issued").order("created_at", { ascending: false }).limit(50),
  ]);
  const all = ((ledgerRows ?? []) as { id: string; month: string; amount: number; paid: number; due_date?: string | null; label?: string | null }[]).map((r) => ({
    ...r,
    amount: Number(r.amount),
    paid: Number(r.paid),
  }));
  const receipts = ((bills ?? []) as Invoice[]).map(normalizeInvoice);

  const plan: FeePlan = (child.fee_plan as FeePlan | undefined) ?? "monthly";
  const ledger = all.filter((r) => r.month <= current);
  // Monthly: this month's fee. Other plans: the next payment still open (else this month's).
  const openRows = [...all].filter((r) => balanceOf(r) > 0).sort((a, b) => rowDue(a).localeCompare(rowDue(b)));
  const thisRow =
    plan === "monthly"
      ? (ledger.find((r) => r.month === current) ??
        (Number(child.monthly_fee) > 0 ? { id: "new", month: current, amount: Number(child.monthly_fee), paid: 0, due_date: null, label: null } : null))
      : (openRows.find((r) => r.month >= current) ?? all.find((r) => r.month === current) ?? null);
  const earlier = ledger.filter((r) => r.month < current && balanceOf(r) > 0 && r.id !== thisRow?.id);
  const earlierDue = earlier.reduce((s, r) => s + balanceOf(r), 0);
  const status = thisRow ? feeStatus(thisRow.amount, thisRow.paid, thisRow.month, today, thisRow.due_date) : null;
  const schedule = plan === "monthly" ? [] : [...all].sort((a, b) => rowDue(a).localeCompare(rowDue(b)));

  const academy = academyDetails();
  const qr = upiIsPlaceholder(academy.upiId) ? null : await qrDataUrl(upiLink(academy.upiId, thisRow ? balanceOf(thisRow) + earlierDue : undefined, child.code ?? undefined));

  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent/fees" />
      <div className="mx-auto max-w-lg px-4">
        {thisRow && status ? (
          <Card className="mt-4 p-4">
            <div className="flex items-center justify-between">
              <p className="font-bold text-navy">{plan === "monthly" ? monthLabel(thisRow.month) : (thisRow.label ?? t("fees.p.nextPayment"))}</p>
              <FeeStatusChip status={status} />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-field bg-field p-2">
                <p className="text-[11px] font-semibold text-muted">{t("fees.col.fee")}</p>
                <p className="font-extrabold">{rupees(thisRow.amount)}</p>
              </div>
              <div className="rounded-field bg-ok-soft p-2">
                <p className="text-[11px] font-semibold text-muted">{t("fees.col.paid")}</p>
                <p className="font-extrabold text-ok">{rupees(thisRow.paid)}</p>
              </div>
              <div className={`rounded-field p-2 ${balanceOf(thisRow) > 0 ? "bg-warn-soft" : "bg-field"}`}>
                <p className="text-[11px] font-semibold text-muted">{t("fees.col.balance")}</p>
                <p className={`font-extrabold ${balanceOf(thisRow) > 0 ? "text-warn" : ""}`}>{rupees(balanceOf(thisRow))}</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted">
              {t("fees.p.dueDate")} <span className="font-semibold text-fg">{dateLabel(rowDue(thisRow))}</span>
              {status === "overdue" && <span className="font-semibold text-danger"> · {t("fees.status.overdue")}</span>}
            </p>
          </Card>
        ) : (
          <Card className="mt-4 p-4 text-sm text-muted">{plan === "monthly" ? t("fees.p.noFeeMonth") : t("fees.p.allDone")}</Card>
        )}

        {plan === "monthly" && earlier.length > 0 && (
          <Section title={t("fees.p.earlierPending", { amount: rupees(earlierDue) })}>
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

        {schedule.length > 0 && (
          <Section title={`${t("fees.p.paymentPlan")} · ${t(`fees.plan.${plan}`)}`}>
            <Card className="divide-y divide-line">
              {schedule.map((r) => {
                const st = feeStatus(r.amount, r.paid, r.month, today, r.due_date);
                return (
                  <div key={r.id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                    <div className="min-w-0">
                      <p className="font-semibold">{r.label ?? monthLabel(r.month)}</p>
                      <p className="text-xs text-muted">{t("fees.bf.dueOn", { date: dateLabel(rowDue(r)) })}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold">{rupees(r.amount)}</p>
                      <FeeStatusChip status={st} />
                    </div>
                  </div>
                );
              })}
            </Card>
          </Section>
        )}

        <Section title={t("fees.p.receipts")}>
          {receipts.length === 0 ? (
            <Empty icon={ReceiptText}>{t("fees.p.noReceipts")}</Empty>
          ) : (
            <Card className="divide-y divide-line overflow-hidden">
              {receipts.map((b) => (
                <a key={b.id} href={`/api/bills/${b.id}/pdf`} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
                  <div className="min-w-0 flex-1">
                    <p className="font-bold text-navy">{b.number}</p>
                    <p className="text-xs text-muted">
                      {monthLabel(b.month)} · {t("fees.p.paidOn", { date: dateLabel(b.paid_on) })}
                    </p>
                  </div>
                  <span className="font-bold">{rupees(b.received)}</span>
                  <Download size={17} className="text-primary" aria-label={t("fees.p.downloadPdf")} />
                </a>
              ))}
            </Card>
          )}
        </Section>

        <Section title={t("fees.p.howToPay")}>
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1 text-sm">
                <p>
                  <span className="text-muted">UPI ID: </span>
                  <span className="font-bold">{academy.upiId}</span>
                </p>
                <p>
                  <span className="text-muted">{t("fees.p.bank")}: </span>
                  <span className="font-semibold">{academy.bankName}</span>
                </p>
                <p>
                  <span className="text-muted">{t("fees.p.accountName")}: </span>
                  <span className="font-semibold">{academy.accountName}</span>
                </p>
                <p>
                  <span className="text-muted">{t("fees.p.accountNo")}: </span>
                  <span className="font-semibold">{academy.accountNumber}</span>
                </p>
                <p>
                  <span className="text-muted">IFSC: </span>
                  <span className="font-semibold">{academy.ifsc}</span>
                </p>
              </div>
              {qr ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={qr} alt={t("fees.p.qrAlt")} width={112} height={112} className="rounded-md border border-line p-1" />
              ) : (
                <div className="grid h-28 w-28 shrink-0 place-items-center rounded-md border-2 border-dashed border-faint text-center text-[11px] font-bold text-faint">[UPI QR CODE]</div>
              )}
            </div>
            <p className="mt-3 text-xs text-muted">
              {t("fees.p.afterPaying")}
            </p>
          </Card>
        </Section>
      </div>
    </>
  );
}
