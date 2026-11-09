import Link from "next/link";
import { Plus, ReceiptText, Search } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { normalizeInvoice } from "@/lib/fees-data";
import { PAYMENT_MODE_LABEL } from "@/lib/fees";
import { dateLabel, monthLabel, rupees } from "@/lib/format";
import { Card, Chip, Empty, FilterChips, Page, PageHeader, Table, Td } from "@/components/ui";
import type { Invoice } from "@/lib/types";

export const metadata = { title: "Billing" };

const PAGE = 100;

export default async function BillingPage({ searchParams }: { searchParams: Promise<{ q?: string; status?: string; month?: string; page?: string }> }) {
  await requirePermission("bills.create");
  const sp = await searchParams;
  const q = (sp.q ?? "").trim().replace(/[%,()*]/g, " ").trim();
  const status = sp.status === "issued" || sp.status === "cancelled" ? sp.status : null;
  const month = sp.month && /^\d{4}-\d{2}$/.test(sp.month) ? sp.month : null;
  const page = Math.max(0, Number(sp.page ?? 0) || 0);

  let query = adminClient().from("invoices").select("*", { count: "exact" }).order("created_at", { ascending: false });
  if (status) query = query.eq("status", status);
  if (month) query = query.eq("month", `${month}-01`);
  if (q) query = query.or(`number.ilike.%${q}%,student_name.ilike.%${q}%,student_code.ilike.%${q}%`);
  const { data, count } = await query.range(page * PAGE, page * PAGE + PAGE - 1);
  const bills = ((data ?? []) as Invoice[]).map(normalizeInvoice);
  const total = bills.filter((b) => b.status === "issued").reduce((s, b) => s + b.received, 0);

  const href = (p: Record<string, string | null>) => {
    const params = new URLSearchParams();
    const merged = { q: q || null, status, month, ...p };
    for (const [k, v] of Object.entries(merged)) if (v) params.set(k, v);
    const s = params.toString();
    return s ? `/billing?${s}` : "/billing";
  };

  return (
    <>
      <PageHeader
        title="Billing"
        subtitle="Every bill in one running series. Bills are never deleted."
        right={
          <Link href="/billing/new" className="btn btn-primary">
            <Plus size={16} /> New bill
          </Link>
        }
      />
      <Page wide>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <FilterChips
            items={[
              { href: href({ status: null, page: null }), label: "All", active: !status },
              { href: href({ status: "issued", page: null }), label: "Issued", active: status === "issued" },
              { href: href({ status: "cancelled", page: null }), label: "Cancelled", active: status === "cancelled" },
            ]}
          />
          <form action="/billing" className="flex flex-wrap items-center gap-2">
            {status && <input type="hidden" name="status" value={status} />}
            <input type="month" name="month" defaultValue={month ?? ""} className="field w-auto py-2" aria-label="Fee month" />
            <div className="relative flex-1 lg:w-64">
              <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-faint" />
              <input name="q" defaultValue={q} placeholder="Bill no., name or ID" className="field pl-9" />
            </div>
            <button className="btn btn-ghost">Search</button>
          </form>
        </div>
        <p className="mt-3 text-sm text-muted">
          {count ?? 0} bill{count === 1 ? "" : "s"}
          {bills.length ? ` · received on this page ${rupees(total)}` : ""}
        </p>

        <div className="mt-3">
          {bills.length === 0 ? (
            <Empty icon={ReceiptText}>No bills found.</Empty>
          ) : (
            <>
              <div className="hidden lg:block">
                <Table head={["Bill no.", "Student", "Month", "Paid on", "Mode", "Received", "Status"]}>
                  {bills.map((b) => (
                    <tr key={b.id} className="hover:bg-field/60">
                      <Td>
                        <Link href={`/billing/${b.id}`} className="font-bold text-primary">
                          {b.number}
                        </Link>
                      </Td>
                      <Td>
                        <p className="font-semibold">{b.student_name}</p>
                        <p className="text-xs text-muted">{b.student_code}</p>
                      </Td>
                      <Td className="whitespace-nowrap">{monthLabel(b.month)}</Td>
                      <Td className="whitespace-nowrap">{dateLabel(b.paid_on)}</Td>
                      <Td>{b.modes.map((m) => PAYMENT_MODE_LABEL[m]).join(", ")}</Td>
                      <Td className={`font-bold ${b.status === "cancelled" ? "text-faint line-through" : ""}`}>{rupees(b.received)}</Td>
                      <Td>
                        {b.status === "cancelled" ? (
                          <div>
                            <Chip tone="danger">Cancelled</Chip>
                            <p className="mt-0.5 max-w-48 truncate text-xs text-muted" title={b.cancelled_reason ?? ""}>
                              {b.cancelled_reason}
                            </p>
                          </div>
                        ) : (
                          <Chip tone="ok">Issued</Chip>
                        )}
                      </Td>
                    </tr>
                  ))}
                </Table>
              </div>
              <Card className="divide-y divide-line overflow-hidden lg:hidden">
                {bills.map((b) => (
                  <Link key={b.id} href={`/billing/${b.id}`} className="flex items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-navy">
                        {b.number} {b.status === "cancelled" && <Chip tone="danger">Cancelled</Chip>}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {b.student_name} · {b.student_code} · {monthLabel(b.month)}
                      </p>
                      {b.status === "cancelled" && <p className="truncate text-xs text-danger">{b.cancelled_reason}</p>}
                    </div>
                    <p className={`font-bold ${b.status === "cancelled" ? "text-faint line-through" : ""}`}>{rupees(b.received)}</p>
                  </Link>
                ))}
              </Card>
            </>
          )}
        </div>

        {(count ?? 0) > PAGE && (
          <div className="mt-4 flex justify-between">
            {page > 0 ? (
              <Link href={href({ page: String(page - 1) })} className="btn btn-ghost">
                Newer
              </Link>
            ) : (
              <span />
            )}
            {(page + 1) * PAGE < (count ?? 0) && (
              <Link href={href({ page: String(page + 1) })} className="btn btn-ghost">
                Older
              </Link>
            )}
          </div>
        )}
      </Page>
    </>
  );
}
