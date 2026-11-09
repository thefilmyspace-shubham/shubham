import { describe, expect, it } from "vitest";
import { parseSearchQuery } from "../search";
import { looksLikeFeeMessage, seenSummary, staffCanPost, staffCanRead, tickState } from "../groups";
import { resolvePermissions, type Role } from "../permissions";

describe("home search parsing", () => {
  it("reads student IDs (current or earlier)", () => {
    expect(parseSearchQuery("CB12-087-26")).toEqual({ kind: "id", code: "CB12-087-26" });
    expect(parseSearchQuery(" mp9-025-26 ")).toEqual({ kind: "id", code: "MP9-025-26" });
  });
  it("reads classes", () => {
    expect(parseSearchQuery("9")).toEqual({ kind: "class", board: null, cls: 9 });
    expect(parseSearchQuery("MP9")).toEqual({ kind: "class", board: "MP", cls: 9 });
    expect(parseSearchQuery("CB 12")).toEqual({ kind: "class", board: "CB", cls: 12 });
    expect(parseSearchQuery("class 10")).toEqual({ kind: "class", board: null, cls: 10 });
    expect(parseSearchQuery("cbse 11")).toEqual({ kind: "class", board: "CB", cls: 11 });
  });
  it("reads mobile numbers", () => {
    expect(parseSearchQuery("98765")).toEqual({ kind: "mobile", digits: "98765" });
    expect(parseSearchQuery("+91 98765 43210")).toEqual({ kind: "mobile", digits: "9876543210" });
    expect(parseSearchQuery("1234")).toEqual({ kind: "name", text: "1234" });
  });
  it("falls back to names", () => {
    expect(parseSearchQuery("Rahul Sharma")).toEqual({ kind: "name", text: "Rahul Sharma" });
    expect(parseSearchQuery("a")).toBeNull();
    expect(parseSearchQuery("   ")).toBeNull();
  });
});

describe("fee messages are blocked in batch groups", () => {
  it.each([
    "Fees of ₹2500 pending for Rahul",
    "Rahul fee 2500 due",
    "Please pay Rs. 1500 by Friday",
    "Rs 1500 balance",
    "Balance due 1,500 for this month",
    "2500/- pending",
    "Pending 3200 for November",
  ])("blocks %s", (text) => expect(looksLikeFeeMessage(text)).toBe(true));
  it.each([
    "Physics test on 12 Nov at 8:00 AM, chapters 3 and 4",
    "Holiday on Monday for Diwali",
    "Timetable changed: Chemistry moves to 4 PM",
    "Pending chapters 5, 6 will be done next week",
    "Board exam starts 2027 March",
  ])("allows %s", (text) => expect(looksLikeFeeMessage(text)).toBe(false));
});

describe("group rules", () => {
  const who = (role: Role) => ({ role, perms: resolvePermissions(role, {}, {}) });
  it("only management and admin post in batch groups", () => {
    expect(staffCanPost(who("admin"), "batch")).toBe(true);
    expect(staffCanPost(who("management"), "batch")).toBe(true);
    expect(staffCanPost(who("reception"), "batch")).toBe(false);
    expect(staffCanPost(who("faculty"), "batch")).toBe(false);
    expect(staffCanPost(who("parent"), "batch")).toBe(false);
  });
  it("staff groups by role", () => {
    expect(staffCanRead(who("reception"), "management")).toBe(true);
    expect(staffCanRead(who("faculty"), "management")).toBe(false);
    expect(staffCanRead(who("faculty"), "faculty")).toBe(true);
    expect(staffCanPost(who("faculty"), "faculty")).toBe(true);
    expect(staffCanRead(who("reception"), "batch")).toBe(false);
  });
  it("seen counts only parents of the batch", () => {
    expect(seenSummary(["p1", "p2", "staff"], ["p1", "p2", "p3", "p4"])).toEqual({ seen: 2, total: 4 });
    expect(seenSummary([], [])).toEqual({ seen: 0, total: 0 });
  });
  it("ticks", () => {
    expect(tickState(0, 5)).toBe(1);
    expect(tickState(2, 5)).toBe(2);
    expect(tickState(5, 5)).toBe(3);
  });
});
