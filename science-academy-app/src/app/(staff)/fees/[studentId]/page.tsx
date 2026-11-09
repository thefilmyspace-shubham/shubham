import Link from "next/link";
import { notFound } from "next/navigation";
import { BellRing, PhoneCall, ReceiptText } from "lucide-react";
import { can, canSeeBatch, requirePermission } from "@/lib/auth";
import { staffNames, studentFeeDetail } from "@/lib/fees-data";
import { CALL_OUTCOME_LABEL, PAYMENT_MODE_LABEL, rowDue, type FeePlan } from "@/lib/fees";
import { dateLabel, dateTimeLabel, monthLabel, rupees, todayIst } from "@/lib/format";
import { boardName, formatMobile, maskMobile } from "@/lib/ids";
import { Card, Chip, Empty, Page, PageHeader, Section, Stat } from "@/components/ui";
import { ActionForm } from "../ActionForm";
import { sendFeeReminder } from "../actions";
import { PlanEditor } from "./PlanEditor";

export const metadata = { title: "Student fees" };

const STAGE_LABEL = { reminded: "Reminder sent", called: "Parent called", escalated: "Escalated to admin" } as const;

export default async function StudentFeesPage({ params }: { params: Promise<{ studentId: string }> }) {
  const viewer = await requirePermission("fees.view");
  const { studentId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(studentId)) notFound();
  const today = todayIst();
  const d = await studentFeeDetail(studentId, today);
  if (!d || !canSeeBatch(viewer, d.student.batch_id)) notFound();
  const names = await staffNames([...d.calls.map((c) => c.called_by), ...d.reminders.map((r) => r.created_by), ...d.invoices.map((i) => i.created_by)]);
  const showNumbers = can(viewer, "students.contacts");
  const pending = d.ledger.reduce((t, r) => t + (rowDue(r) <= today || r.month <= today ? r.balance : 0), 0);
  const overdue = d.ledger.filter((r) => r.status === "overdue");
  const totalPaid = d.invoices.filter((i) => i.status === "issued").reduce((s, i) => s + i.received, 0);
  const s = d.student;

  return (
    <>
      <PageHeader title={s.name} subtitle={`${s.code ?? "Draft"} · Class ${s.current_class} · ${boardName(s.board)}`} back="/fees" />
      <Page wide>
        <div className="flex flex-wrap gap-2">
          {can(viewer, "bills.create") && (
            <Link href={`/billing/new?student=${s.id}`} className="btn btn-primary">
              <ReceiptText size={16} /> Make bill
            </Link>
          )}
          <Link href={`/calls?student=${s.id}`} className="btn btn-soft">
            <PhoneCall size={16} /> Call parent
          </Link>
          {pending > 0 && <ActionForm action={sendFeeReminder} fields={{ studentId: s.id }} label="Send reminder" icon={<BellRing size={15} />} className="btn btn-ghost" />}
          <Link href={`/students/${s.id}`} className="btn btn-ghost">
            Profile
          </Link>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label={(s.fee_plan ?? "monthly") === "monthly" ? "Monthly fee" : "Total fee"} value={rupees((s.fee_plan ?? "monthly") === "monthly" ? s.monthly_fee : d.ledger.reduce((t, r) => t + r.amount, 0))} />
          <Stat label="Pending now" value={rupees(pending)} tone={pending > 0 ? "warn" : "ok"} />
          <Stat label="Overdue payments" value={overdue.length} tone={overdue.length ? "danger" : "ok"} />
          <Stat label="Paid (all bills)" value={rupees(totalPaid)} tone="ok" />
        </div>

        <div className="grid grid-cols-1 gap-x-5 lg:grid-cols-[1fr_340px]">
          <div>
            <Section title="Payment plan and due dates">
              <PlanEditor
                studentId={s.id}
                plan={(s.fee_plan as FeePlan | undefined) ?? "monthly"}
                monthlyFee={s.monthly_fee}
                dueDay={s.fee_due_day ?? 5}
                canEdit={can(viewer, "bills.create")}
                // Monthly: newest month first. Other plans: first payment first.
                rows={[...d.ledger]
                  .sort((a, b) => ((s.fee_plan ?? "monthly") === "monthly" ? rowDue(b).localeCompare(rowDue(a)) : rowDue(a).localeCompare(rowDue(b))))
                  .map((r) => ({
                    id: r.id,
                    month: r.month,
                    label: r.label ?? null,
                    due: rowDue(r),
                    amount: r.amount,
                    paid: r.paid,
                    balance: r.balance,
                    status: r.status,
                  }))}
              />
            </Section>

            <Section title="Bills">
              {d.invoices.length === 0 ? (
                <Empty icon={ReceiptText}>No bills yet.</Empty>
              ) : (
                <Card className="divide-y divide-line overflow-hidden">
                  {d.invoices.map((i) => (
                    <Link key={i.id} href={`/billing/${i.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
                      <div className="min-w-0 flex-1">
                        <p className="font-bold text-navy">
                          {i.number} {i.status === "cancelled" && <Chip tone="danger">Cancelled</Chip>}
                        </p>
                        <p className="text-xs text-muted">
                          {monthLabel(i.month)} · {dateLabel(i.paid_on)} · {i.modes.map((m) => PAYMENT_MODE_LABEL[m]).join(", ")} · {names.get(i.created_by) ?? ""}
                        </p>
                        {i.status === "cancelled" && <p className="text-xs text-danger">Reason: {i.cancelled_reason}</p>}
                      </div>
                      <p className={`font-bold ${i.status === "cancelled" ? "text-faint line-through" : ""}`}>{rupees(i.received)}</p>
                    </Link>
                  ))}
                </Card>
              )}
            </Section>
          </div>

          <div>
            <Section title="Parents">
              <Card className="divide-y divide-line">
                {d.guardians.map((g) => (
                  <div key={g.id} className="flex items-center gap-2 px-4 py-2.5 text-sm">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold capitalize">
                        {g.name ?? g.relation} <span className="text-xs font-normal text-muted">({g.relation})</span>
                      </p>
                      <p className="text-muted">{showNumbers ? formatMobile(g.mobile) : maskMobile(g.mobile)}</p>
                    </div>
                    {g.is_login_number ? <Chip tone="primary">Login number</Chip> : <Chip>Contact only</Chip>}
                  </div>
                ))}
                {d.guardians.length === 0 && <p className="px-4 py-3 text-sm text-muted">No numbers saved.</p>}
              </Card>
            </Section>

            <Section title="Calls">
              {d.calls.length === 0 ? (
                <Empty icon={PhoneCall}>No calls yet.</Empty>
              ) : (
                <Card className="divide-y divide-line">
                  {d.calls.map((c) => (
                    <div key={c.id} className="px-4 py-2.5 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold">{CALL_OUTCOME_LABEL[c.outcome]}</span>
                        <span className="text-xs text-muted">Attempt {c.attempt_no}</span>
                      </div>
                      {c.follow_up_date && <p className="text-xs font-semibold text-primary">Promised {dateLabel(c.follow_up_date)}</p>}
                      {c.note && <p className="text-[13px] text-fg">{c.note}</p>}
                      <p className="text-xs text-muted">
                        {dateTimeLabel(c.created_at)} · {names.get(c.called_by) ?? ""}
                      </p>
                    </div>
                  ))}
                </Card>
              )}
            </Section>

            <Section title="Reminder history">
              {d.reminders.length === 0 ? (
                <Empty icon={BellRing}>No reminders yet.</Empty>
              ) : (
                <Card className="divide-y divide-line">
                  {d.reminders.map((r) => (
                    <div key={r.id} className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm">
                      <div>
                        <p className="font-semibold">{STAGE_LABEL[r.stage]}</p>
                        <p className="text-xs text-muted">
                          {monthLabel(r.month)} fee · {r.created_by ? names.get(r.created_by) : "System"}
                        </p>
                      </div>
                      <span className="text-xs text-muted">{dateTimeLabel(r.created_at)}</span>
                    </div>
                  ))}
                </Card>
              )}
            </Section>
          </div>
        </div>
      </Page>
    </>
  );
}
