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
