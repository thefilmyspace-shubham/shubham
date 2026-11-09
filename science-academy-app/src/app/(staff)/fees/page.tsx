import Link from "next/link";
import { BellRing, ChevronLeft, ChevronRight, IndianRupee, Plus, Search } from "lucide-react";
import { can, canSeeBatch, requirePermission } from "@/lib/auth";
import { ensureLedgerForMonth, feeListForMonth } from "@/lib/fees-data";
import { FEE_STATUS_LABEL, dueDate, type FeeStatus } from "@/lib/fees";
import { addMonths, dateLabel, monthLabel, monthStart, rupees, todayIst } from "@/lib/format";
import { boardName, parseStudentId } from "@/lib/ids";
import { Card, Empty, FilterChips, Page, PageHeader, Section, Stat, Table, Td } from "@/components/ui";
import { Meter } from "@/components/BarChart";
import { FeeStatusChip } from "./StatusChip";
import { ActionForm } from "./ActionForm";
import { remindAllOverdue, sendFeeReminder } from "./actions";

export const metadata = { title: "Fees" };

const STATUSES: FeeStatus[] = ["paid", "partial", "pending", "overdue"];

export default async function FeesPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const viewer = await requirePermission("fees.view");
  const sp = await searchParams;
  const today = todayIst();
  const current = monthStart(today);
  const month = sp.month && /^\d{4}-\d{2}$/.test(sp.month) ? `${sp.month}-01` : current;
  const status = STATUSES.includes(sp.status as FeeStatus) ? (sp.status as FeeStatus) : null;
  const q = (sp.q ?? "").trim();

  if (month === current) await ensureLedgerForMonth(month);
  const all = (await feeListForMonth(month, today)).filter((r) => canSeeBatch(viewer, r.student.batch_id));

  const counts = Object.fromEntries(STATUSES.map((s) => [s, all.filter((r) => r.status === s).length])) as Record<FeeStatus, number>;
  const expected = all.reduce((s, r) => s + r.ledger.amount, 0);
  const collected = all.reduce((s, r) => s + Math.min(r.ledger.paid, r.ledger.amount), 0);
  const pending = all.reduce((s, r) => s + r.balance, 0);

  const needle = q.toLowerCase().replace(/\s+/g, "");
  const parsed = parseStudentId(q);
  const rows = all.filter(
    (r) =>
      (!status || r.status === status) &&
      (!q ||
        r.student.name.toLowerCase().includes(q.toLowerCase()) ||
        (r.student.code ?? "").toLowerCase().includes(needle) ||
        (parsed !== null && r.student.code?.toUpperCase() === q.toUpperCase())),
  );

  // Pending amounts by class.
  const byClass = new Map<string, { board: string; cls: number; amount: number; students: number }>();
  for (const r of all) {
    if (r.balance <= 0) continue;
    const key = `${r.student.board}-${r.student.current_class}`;
    const e = byClass.get(key) ?? { board: r.student.board, cls: r.student.current_class, amount: 0, students: 0 };
    e.amount += r.balance;
    e.students += 1;
    byClass.set(key, e);
  }
  const classRows = [...byClass.values()].sort((a, b) => b.amount - a.amount);
  const topClass = classRows[0]?.amount ?? 0;

  const ym = month.slice(0, 7);
  const href = (p: Record<string, string | null>) => {
    const params = new URLSearchParams();
    const merged = { month: ym, status: status ?? null, q: q || null, ...p };
    for (const [k, v] of Object.entries(merged)) if (v) params.set(k, v);
    return `/fees?${params.toString()}`;
  };
  const canBill = can(viewer, "bills.create");

  return (
    <>
      <PageHeader
        title="Fees"
        subtitle={`${monthLabel(month)} · due ${dateLabel(dueDate(month))}`}
        right={
          canBill ? (
            <Link href="/billing/new" className="btn btn-primary">
              <Plus size={16} /> <span className="hidden sm:inline">Make bill</span>
            </Link>
          ) : null
        }
      />
      <Page wide>
        <div className="flex flex-wrap items-center gap-2">
          <Link href={href({ month: addMonths(month, -1).slice(0, 7) })} className="btn btn-ghost px-2.5" aria-label="Previous month">
            <ChevronLeft size={17} />
          </Link>
          <form action="/fees" className="flex items-center gap-2">
            <input type="month" name="month" defaultValue={ym} className="field w-auto py-2" />
            {q && <input type="hidden" name="q" value={q} />}
            <button className="btn btn-ghost">Go</button>
          </form>
          <Link href={href({ month: addMonths(month, 1).slice(0, 7) })} className="btn btn-ghost px-2.5" aria-label="Next month">
            <ChevronRight size={17} />
          </Link>
          {month !== current && (
            <Link href={href({ month: current.slice(0, 7) })} className="text-sm font-bold text-primary">
              This month
            </Link>
          )}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Fee this month" value={rupees(expected)} hint={`${all.length} students`} />
          <Stat label="Collected" value={rupees(collected)} tone="ok" hint={`${counts.paid} paid in full`} />
          <Stat label="Pending" value={rupees(pending)} tone="warn" hint={`${counts.partial + counts.pending + counts.overdue} students`} />
          <Stat label="Overdue" value={counts.overdue} tone="danger" hint="after the 5th" href={href({ status: "overdue" })} />
        </div>

        <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <FilterChips
            items={[
              { href: href({ status: null }), label: "All", count: all.length, active: !status },
              ...STATUSES.map((s) => ({ href: href({ status: s }), label: FEE_STATUS_LABEL[s], count: counts[s], active: status === s })),
            ]}
          />
          <form action="/fees" className="flex items-center gap-2">
            <input type="hidden" name="month" value={ym} />
            {status && <input type="hidden" name="status" value={status} />}
            <div className="relative flex-1 lg:w-72">
              <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-faint" />
              <input name="q" defaultValue={q} placeholder="Name or student ID" className="field pl-9" />
            </div>
          </form>
        </div>

        {month === current && counts.overdue > 0 && (
          <div className="mt-3">
            <ActionForm
              action={remindAllOverdue}
              fields={{}}
              label={`Remind all overdue parents privately`}
              icon={<BellRing size={15} />}
              confirm="Send a private fee reminder to every parent with an overdue fee? (Never posted in batch groups.)"
            />
          </div>
        )}

        <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_300px]">
          <div>
            {rows.length === 0 ? (
              <Empty icon={IndianRupee}>{all.length === 0 ? "No fee rows for this month." : "No students match."}</Empty>
            ) : (
              <>
                <div className="hidden lg:block">
                  <Table head={["Student", "Class", "Fee", "Paid", "Balance", "Status", ""]}>
                    {rows.map((r) => (
                      <tr key={r.ledger.id} className="hover:bg-field/60">
                        <Td>
                          <Link href={`/fees/${r.student.id}`} className="font-bold text-navy hover:text-primary">
                            {r.student.name}
                          </Link>
                          <p className="text-xs text-muted">{r.student.code}</p>
                        </Td>
                        <Td className="whitespace-nowrap">
                          {r.student.current_class} · {r.student.board === "CB" ? "CBSE" : "MP"}
                        </Td>
                        <Td>{rupees(r.ledger.amount)}</Td>
                        <Td>{rupees(r.ledger.paid)}</Td>
                        <Td className={r.balance > 0 ? "font-bold" : "text-muted"}>{rupees(r.balance)}</Td>
                        <Td>
                          <FeeStatusChip status={r.status} />
                        </Td>
                        <Td>
                          <div className="flex justify-end gap-2">
                            {canBill && r.balance > 0 && (
                              <Link href={`/billing/new?student=${r.student.id}&month=${ym}`} className="btn btn-soft px-3 py-1.5 text-[13px]">
                                Bill
                              </Link>
                            )}
                            {r.balance > 0 && month === current && (
                              <ActionForm action={sendFeeReminder} fields={{ studentId: r.student.id }} label="Remind" className="btn btn-ghost px-3 py-1.5 text-[13px]" />
                            )}
                          </div>
                        </Td>
                      </tr>
                    ))}
                  </Table>
                </div>
                <Card className="divide-y divide-line overflow-hidden lg:hidden">
                  {rows.map((r) => (
                    <Link key={r.ledger.id} href={`/fees/${r.student.id}`} className="flex items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-bold text-navy">{r.student.name}</p>
                        <p className="text-xs text-muted">
                          {r.student.code} · Class {r.student.current_class}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold">{r.balance > 0 ? rupees(r.balance) : rupees(r.ledger.paid)}</p>
                        <FeeStatusChip status={r.status} />
                      </div>
                    </Link>
                  ))}
                </Card>
              </>
            )}
          </div>

          <div>
            <Section title="Pending by class" className="pt-0">
              <Card className="space-y-3 p-4">
                {classRows.length === 0 && <p className="text-sm text-muted">Nothing pending.</p>}
                {classRows.map((c) => (
                  <div key={`${c.board}${c.cls}`}>
                    <div className="mb-1 flex items-baseline justify-between text-sm">
                      <span className="font-semibold">
                        {boardName(c.board)} {c.cls}
                      </span>
                      <span className="font-bold">{rupees(c.amount)}</span>
                    </div>
                    <Meter value={c.amount} max={topClass} tone="warn" />
                    <p className="mt-0.5 text-[11.5px] text-muted">
                      {c.students} student{c.students === 1 ? "" : "s"}
                    </p>
                  </div>
                ))}
              </Card>
            </Section>
          </div>
        </div>
      </Page>
    </>
  );
}
