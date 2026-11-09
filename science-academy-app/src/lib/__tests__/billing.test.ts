import { describe, expect, it } from "vitest";
import { billPreview, callBucket, orderCallList, overdueMonths, overdueSummary, upiLink, validModes, type CallItem } from "../billing-calc";

describe("bill preview", () => {
  it("works out the balance", () => {
    expect(billPreview(2500, 1000, 1000)).toMatchObject({ balanceBefore: 1500, balanceAfter: 500, error: null });
    expect(billPreview(2500, 0, 2500)).toMatchObject({ balanceAfter: 0, error: null });
  });
  it("refuses impossible bills", () => {
    expect(billPreview(2500, 2500, 100).error).toMatch(/already fully paid/);
    expect(billPreview(2500, 1000, 2000).error).toMatch(/more than the balance/);
    expect(billPreview(2500, 0, 0).error).toMatch(/amount received/);
    expect(billPreview(0, 0, 100).error).toMatch(/fee amount/);
    expect(billPreview(800, 1000, 100).error).toMatch(/less than what is already paid/);
  });
  it("needs a payment mode", () => {
    expect(validModes([])).toBe(false);
    expect(validModes(["upi", "cash"])).toBe(true);
    expect(validModes(["cheque"])).toBe(false);
  });
});

describe("overdue", () => {
  const rows = [
    { month: "2026-11-01", amount: 2500, paid: 0 },
    { month: "2026-09-01", amount: 2500, paid: 2500 },
    { month: "2026-10-01", amount: 2500, paid: 1000 },
  ];
  it("lists unpaid months past the 5th, oldest first", () => {
    expect(overdueMonths(rows, "2026-11-04").map((r) => r.month)).toEqual(["2026-10-01"]);
    expect(overdueMonths(rows, "2026-11-06").map((r) => r.month)).toEqual(["2026-10-01", "2026-11-01"]);
  });
  it("sums what is overdue", () => {
    expect(overdueSummary(rows, "2026-11-06")).toEqual({ oldestMonth: "2026-10-01", totalDue: 4000, daysLate: 32 });
    expect(overdueSummary([{ month: "2026-11-01", amount: 2500, paid: 0 }], "2026-11-05")).toBeNull();
  });
});

describe("call list order", () => {
  const base: CallItem = { studentId: "a", oldestMonth: "2026-10-01", totalDue: 2500, daysLate: 10, attempts: 0, lastOutcome: null, followUpDate: null };
  const today = "2026-11-09";
  it("puts promises due today on top, then longest overdue", () => {
    const items: CallItem[] = [
      { ...base, studentId: "short", daysLate: 4 },
      { ...base, studentId: "long", daysLate: 35 },
      { ...base, studentId: "promise-today", daysLate: 2, lastOutcome: "promised_date", followUpDate: "2026-11-09" },
      { ...base, studentId: "promise-later", daysLate: 60, lastOutcome: "promised_date", followUpDate: "2026-11-15" },
      { ...base, studentId: "escalated", daysLate: 90, lastOutcome: "needs_admin" },
    ];
    expect(orderCallList(items, today).map((i) => i.studentId)).toEqual(["promise-today", "long", "short", "escalated", "promise-later"]);
  });
  it("a broken promise comes back to the top", () => {
    expect(callBucket({ ...base, lastOutcome: "promised_date", followUpDate: "2026-11-01" }, today)).toBe("promised_due");
    expect(callBucket({ ...base, lastOutcome: "not_connected" }, today)).toBe("call");
  });
  it("bigger amount breaks a tie", () => {
    const items = [
      { ...base, studentId: "small", totalDue: 1000 },
      { ...base, studentId: "big", totalDue: 5000 },
    ];
    expect(orderCallList(items, today)[0].studentId).toBe("big");
  });
});

describe("UPI link", () => {
  it("is a upi:// payment link", () => {
    expect(upiLink("academy@okhdfc")).toBe("upi://pay?pa=academy@okhdfc&pn=Science%20Academy&cu=INR");
    expect(upiLink("academy@okhdfc", 2500)).toContain("am=2500.00");
  });
});
