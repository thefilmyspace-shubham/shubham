import { describe, expect, it } from "vitest";
import { ledgerRowsFor, parseFeePlan } from "../fee-plan-form";

const fd = (o: Record<string, string>) => {
  const f = new FormData();
  for (const [k, v] of Object.entries(o)) f.set(k, v);
  return f;
};

describe("fee plan on the registration form", () => {
  it("monthly with a due day", () => {
    const r = parseFeePlan(fd({ fee_plan: "monthly", monthly_fee: "2500", fee_due_day: "10" }), true);
    expect(r.ok && r.data).toMatchObject({ fee_plan: "monthly", monthly_fee: 2500, fee_due_day: 10 });
    if (r.ok) expect(ledgerRowsFor("s1", r.data, "2026-11-20")).toEqual([
      { student_id: "s1", month: "2026-11-01", amount: 2500, due_date: "2026-11-10", label: null, installment_no: null },
    ]);
  });
  it("monthly needs a fee to register, not for a draft", () => {
    expect(parseFeePlan(fd({ fee_plan: "monthly", monthly_fee: "" }), true).ok).toBe(false);
    expect(parseFeePlan(fd({ fee_plan: "monthly", monthly_fee: "" }), false).ok).toBe(true);
  });
  it("installments become one row per payment", () => {
    const schedule = JSON.stringify([
      { due_date: "2027-02-10", amount: 8000, label: "Installment 2 of 2" },
      { due_date: "2026-12-10", amount: 10000, label: "Installment 1 of 2" },
    ]);
    const r = parseFeePlan(fd({ fee_plan: "installments", fee_schedule: schedule }), true);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.data.total_fee).toBe(18000);
    expect(r.data.monthly_fee).toBe(0);
    const rows = ledgerRowsFor("s1", r.data, "2026-11-20");
    expect(rows.map((x) => [x.month, x.due_date, x.amount, x.installment_no])).toEqual([
      ["2026-12-01", "2026-12-10", 10000, 1],
      ["2027-02-01", "2027-02-10", 8000, 2],
    ]);
  });
  it("one time keeps a single payment", () => {
    const r = parseFeePlan(fd({ fee_plan: "one_time", fee_schedule: JSON.stringify([{ due_date: "2026-12-01", amount: 30000 }]) }), true);
    expect(r.ok && r.data.fee_schedule).toEqual([{ due_date: "2026-12-01", amount: 30000, label: "Full fee (one time)" }]);
  });
  it("refuses an empty or same-month schedule when registering", () => {
    expect(parseFeePlan(fd({ fee_plan: "manual", fee_schedule: "[]" }), true).ok).toBe(false);
    const same = JSON.stringify([
      { due_date: "2026-12-05", amount: 1000 },
      { due_date: "2026-12-20", amount: 1000 },
    ]);
    const r = parseFeePlan(fd({ fee_plan: "manual", fee_schedule: same }), true);
    expect(!r.ok && r.errors.fee_schedule).toMatch(/one payment per month/);
  });
});
