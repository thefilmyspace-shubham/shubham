import { describe, expect, it } from "vitest";
import { formatStudentId, normalizeMobile, parseStaffId, parseStudentId, promotedId, sessionLabel, sessionYearFor } from "../ids";

describe("student IDs", () => {
  it("formats like the spec", () => {
    expect(formatStudentId("MP", 9, 25, 26)).toBe("MP9-025-26");
    expect(formatStudentId("CB", 12, 87, 26)).toBe("CB12-087-26");
    expect(formatStudentId("CB", 10, 1000, 27)).toBe("CB10-1000-27");
  });
  it("parses in any case", () => {
    expect(parseStudentId("mp9-025-26")).toEqual({ board: "MP", cls: 9, roll: 25, session: 26 });
    expect(parseStudentId("CB12-087-26")).toEqual({ board: "CB", cls: 12, roll: 87, session: 26 });
    expect(parseStudentId("CB5-087-26")).toBeNull();
    expect(parseStudentId("Rahul")).toBeNull();
  });
  it("promotion keeps the roll", () => {
    expect(promotedId({ board: "MP", cls: 9, roll: 25, session: 26 })).toEqual({ board: "MP", cls: 10, roll: 25, session: 27 });
    expect(promotedId({ board: "CB", cls: 12, roll: 1, session: 26 })).toBeNull();
  });
  it("session starts in April (IST)", () => {
    expect(sessionYearFor(new Date("2026-11-09T10:00:00Z"))).toBe(26);
    expect(sessionYearFor(new Date("2027-02-01T10:00:00Z"))).toBe(26);
    expect(sessionYearFor(new Date("2027-03-31T19:00:00Z"))).toBe(27); // 1 Apr in India
    expect(sessionLabel(26)).toBe("2026-27");
  });
});

describe("mobiles and staff IDs", () => {
  it("normalises Indian mobiles", () => {
    expect(normalizeMobile("+91 98765 43210")).toBe("9876543210");
    expect(normalizeMobile("09876543210")).toBe("9876543210");
    expect(normalizeMobile("12345")).toBeNull();
    expect(normalizeMobile("5876543210")).toBeNull();
  });
  it("reads staff IDs", () => {
    expect(parseStaffId("ad-1")).toBe("AD-01");
    expect(parseStaffId("FC07")).toBe("FC-07");
    expect(parseStaffId("XY-01")).toBeNull();
  });
});
