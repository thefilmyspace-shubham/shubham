import { requirePermission, canSeeBatch } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { monthStart, todayIst } from "@/lib/format";
import { Page, PageHeader } from "@/components/ui";
import { monthPayments } from "@/lib/fees-data";
import type { MonthInfo, StudentHit } from "../actions";
import { BillForm } from "./BillForm";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "New bill" };

export default async function NewBillPage({ searchParams }: { searchParams: Promise<{ student?: string; month?: string }> }) {
  const viewer = await requirePermission("bills.create");
  const { t } = await getT();
  const sp = await searchParams;
  const today = todayIst();
  let initial: StudentHit | null = null;
  if (sp.student && /^[0-9a-f-]{36}$/i.test(sp.student)) {
    const { data } = await adminClient()
      .from("students")
      .select("id, name, code, board, current_class, monthly_fee, batch_id, status")
      .eq("id", sp.student)
      .maybeSingle();
    if (data && data.status !== "draft" && canSeeBatch(viewer, data.batch_id)) {
      initial = { id: data.id, name: data.name, code: data.code, board: data.board, cls: data.current_class, monthlyFee: Number(data.monthly_fee ?? 0) };
    }
  }
  const month = sp.month && /^\d{4}-\d{2}$/.test(sp.month) ? sp.month : monthStart(today).slice(0, 7);
  let info: MonthInfo | null = null;
  if (initial) {
    const m = await monthPayments(initial.id, `${month}-01`);
    info = {
      amount: m.amount,
      paid: m.paid,
      bills: m.invoices.map((i) => ({ id: i.id, number: i.number, received: i.received, paidOn: i.paid_on, status: i.status })),
    };
  }
  return (
    <>
      <PageHeader title={t("fees.billing.newBill")} subtitle={t("fees.billing.feeReceipt")} back="/billing" />
      <Page wide>
        <BillForm initialStudent={initial} initialMonth={month} initialInfo={info} today={today} />
      </Page>
    </>
  );
}
