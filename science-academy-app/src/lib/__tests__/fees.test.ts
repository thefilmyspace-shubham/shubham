import { describe, expect, it } from "vitest";
import { daysLate, dueDate, feeStatus, invoiceNumber, rupeesInWords } from "../fees";
import { addMonths, monthStart } from "../format";

describe("fees", () => {
  it("is due on the 5th", () => {
    expect(dueDate("2026-11-01")).toBe("2026-11-05");
  });
  it("works out status", () => {
    expect(feeStatus(2500, 2500, "2026-11-01", "2026-11-20")).toBe("paid");
    expect(feeStatus(2500, 0, "2026-11-01", "2026-11-05")).toBe("pending");
    expect(feeStatus(2500, 1000, "2026-11-01", "2026-11-04")).toBe("partial");
    expect(feeStatus(2500, 1000, "2026-11-01", "2026-11-06")).toBe("overdue");
    expect(feeStatus(2500, 0, "2026-11-01", "2026-11-06")).toBe("overdue");
  });
  it("counts days late", () => {
    expect(daysLate("2026-11-01", "2026-11-05")).toBe(0);
    expect(daysLate("2026-11-01", "2026-11-12")).toBe(7);
  });
  it("numbers bills", () => {
    expect(invoiceNumber(26, 412)).toBe("SA-26-0412");
  });
  it("writes amounts in words", () => {
    expect(rupeesInWords(2500)).toBe("Two thousand five hundred rupees only");
    expect(rupeesInWords(135200)).toBe("One lakh thirty five thousand two hundred rupees only");
  });
  it("month helpers", () => {
    expect(monthStart("2026-11-09")).toBe("2026-11-01");
    expect(addMonths("2026-11-01", 3)).toBe("2027-02-01");
    expect(addMonths("2026-01-01", -1)).toBe("2025-12-01");
  });
});

import { addMonthsToDate, checkSchedule, makeInstallments, rowDue, scheduleTotal } from "../fees";

describe("fee plans", () => {
  it("uses each row's own due date", () => {
    expect(feeStatus(5000, 0, "2026-12-01", "2026-12-12", "2026-12-15")).toBe("pending");
    expect(feeStatus(5000, 0, "2026-12-01", "2026-12-16", "2026-12-15")).toBe("overdue");
    expect(daysLate("2026-12-01", "2026-12-20", "2026-12-15")).toBe(5);
    expect(rowDue({ month: "2026-12-01", due_date: null })).toBe("2026-12-05");
    expect(rowDue({ month: "2026-12-01", due_date: "2026-12-10" })).toBe("2026-12-10");
  });
  it("adds months and keeps the day inside the month", () => {
    expect(addMonthsToDate("2026-11-30", 3)).toBe("2027-02-28");
    expect(addMonthsToDate("2026-12-10", 1)).toBe("2027-01-10");
  });
  it("splits a total into installments", () => {
    const rows = makeInstallments(25000, 3, "2026-12-10", 2);
    expect(rows.map((r) => r.due_date)).toEqual(["2026-12-10", "2027-02-10", "2027-04-10"]);
    expect(rows.map((r) => r.amount)).toEqual([8334, 8333, 8333]);
    expect(scheduleTotal(rows)).toBe(25000);
    expect(rows[2].label).toBe("Installment 3 of 3");
  });
  it("checks a schedule", () => {
    expect(checkSchedule([])).toMatch(/at least one/);
    expect(checkSchedule([{ due_date: "2026-12-10", amount: 0, label: "" }])).toMatch(/amount/);
    expect(
      checkSchedule([
        { due_date: "2026-12-10", amount: 5000, label: "" },
        { due_date: "2026-12-25", amount: 5000, label: "" },
      ]),
    ).toMatch(/one payment per month/);
    expect(checkSchedule(makeInstallments(12000, 4, "2026-12-05"))).toBeNull();
  });
});
