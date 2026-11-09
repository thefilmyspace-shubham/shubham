import { describe, expect, it } from "vitest";
import { bandOf, classSummary, findClashes, percentOf, rankScores, testCoversBatch } from "../academics";
import { attendancePct, canChangeRow, countStatuses, flagsFor, isLocked, trailingAbsences } from "../attendance";
import type { AttendanceRow } from "../types";

describe("ranking", () => {
  it("shares ranks on ties and skips (1, 2, 2, 4)", () => {
    const r = rankScores([
      { studentId: "a", score: 40, absent: false },
      { studentId: "b", score: 48, absent: false },
      { studentId: "c", score: 45, absent: false },
      { studentId: "d", score: 45, absent: false },
    ]);
    expect(r.map((x) => [x.studentId, x.rank])).toEqual([
      ["b", 1],
      ["c", 2],
      ["d", 2],
      ["a", 4],
    ]);
  });
  it("does not rank absent or missing scores", () => {
    const r = rankScores([
      { studentId: "a", score: null, absent: true },
      { studentId: "b", score: 30, absent: false },
      { studentId: "c", score: null, absent: false },
    ]);
    expect(r).toEqual([{ studentId: "b", score: 30, rank: 1 }]);
  });
  it("keeps a zero score", () => {
    expect(rankScores([{ studentId: "a", score: 0, absent: false }])).toHaveLength(1);
  });
});

describe("percent and bands", () => {
  it("percent with one decimal", () => {
    expect(percentOf(42, 50)).toBe(84);
    expect(percentOf(2, 3)).toBe(66.7);
    expect(percentOf(null, 50)).toBeNull();
    expect(percentOf(10, null)).toBeNull();
    expect(percentOf(10, 0)).toBeNull();
  });
  it("bands", () => {
    expect(bandOf(90)).toBe("90+");
    expect(bandOf(89.9)).toBe("75–89");
    expect(bandOf(60)).toBe("60–74");
    expect(bandOf(59.9)).toBe("Below 60");
  });
  it("class summary", () => {
    const s = classSummary(
      [
        { studentId: "a", score: 45, absent: false },
        { studentId: "b", score: 35, absent: false },
        { studentId: "c", score: null, absent: true },
      ],
      50,
    );
    expect(s.appeared).toBe(2);
    expect(s.absent).toBe(1);
    expect(s.average).toBe(80);
    expect(s.highest).toBe(90);
    expect(s.bands["90+"]).toBe(1);
    expect(s.bands["60–74"]).toBe(1);
  });
});

describe("tests and clashes", () => {
  it("flags a School exam and a Coaching test on the same day for one class", () => {
    const clashes = findClashes([
      { board: "CB", class: 9, date: "2026-11-20", tag: "School" },
      { board: "CB", class: 9, date: "2026-11-20", tag: "Coaching" },
      { board: "CB", class: 10, date: "2026-11-20", tag: "Coaching" },
      { board: "MP", class: 9, date: "2026-11-20", tag: "School" },
    ]);
    expect([...clashes]).toEqual(["CB-9-2026-11-20"]);
  });
  it("whole-class tests cover every batch of the class", () => {
    const b = { id: "b1", board: "CB" as const, class: 9 };
    expect(testCoversBatch({ batch_id: null, board: "CB", class: 9 }, b)).toBe(true);
    expect(testCoversBatch({ batch_id: null, board: "MP", class: 9 }, b)).toBe(false);
    expect(testCoversBatch({ batch_id: "b2", board: "CB", class: 9 }, b)).toBe(false);
    expect(testCoversBatch({ batch_id: "b1", board: "CB", class: 9 }, b)).toBe(true);
  });
});

describe("attendance", () => {
  const now = new Date("2026-11-09T10:00:00Z");
  it("locks 24 hours after saving", () => {
    expect(isLocked("2026-11-09T09:59:00Z", now)).toBe(true);
    expect(isLocked("2026-11-09T10:01:00Z", now)).toBe(false);
  });
  it("only correctors change locked rows", () => {
    const locked = { locked_at: "2026-11-08T10:00:00Z" };
    const open = { locked_at: "2026-11-10T08:00:00Z" };
    expect(canChangeRow(null, true, false, now)).toBe(true);
    expect(canChangeRow(null, false, true, now)).toBe(false);
    expect(canChangeRow(open, true, false, now)).toBe(true);
    expect(canChangeRow(locked, true, false, now)).toBe(false);
    expect(canChangeRow(locked, false, true, now)).toBe(true);
  });
  it("late counts as present", () => {
    expect(attendancePct(["P", "L", "A", "A"])).toBe(50);
    expect(attendancePct([])).toBeNull();
  });
  it("counts absences in a row up to the latest day", () => {
    const rows = [
      { date: "2026-11-02", status: "A" as const },
      { date: "2026-11-05", status: "A" as const },
      { date: "2026-11-03", status: "P" as const },
      { date: "2026-11-04", status: "A" as const },
      { date: "2026-11-06", status: "A" as const },
    ];
    expect(trailingAbsences(rows)).toEqual({ count: 3, dates: ["2026-11-04", "2026-11-05", "2026-11-06"] });
    expect(trailingAbsences([{ date: "2026-11-06", status: "L" }]).count).toBe(0);
  });
  it("counts statuses", () => {
    expect(countStatuses(["P", "A", undefined, "L", "P"])).toEqual({ P: 2, A: 1, L: 1, unmarked: 1 });
  });
  it("flags low attendance and streaks", () => {
    const row = (date: string, status: "P" | "A" | "L"): AttendanceRow => ({
      id: date,
      student_id: "s1",
      batch_id: "b",
      date,
      status,
      marked_by: null,
      marked_at: "",
      locked_at: "",
    });
    const f = flagsFor([row("2026-11-01", "P"), row("2026-11-02", "A"), row("2026-11-03", "A"), row("2026-11-04", "A")]).get("s1")!;
    expect(f.pct).toBe(25);
    expect(f.low).toBe(true);
    expect(f.streak).toBe(3);
  });
});

import { parentTestView } from "../academics";

describe("parent rank view", () => {
  const rows = [
    { studentId: "a", score: 90, absent: false },
    { studentId: "b", score: 80, absent: false },
    { studentId: "c", score: 80, absent: false },
    { studentId: "d", score: 70, absent: false },
    { studentId: "e", score: 60, absent: false },
    { studentId: "f", score: 50, absent: false },
    { studentId: "g", score: null, absent: true },
  ];
  it("gives the child's rank out of those who appeared", () => {
    const v = parentTestView(rows, "c", 100);
    expect(v.rank).toBe(2);
    expect(v.outOf).toBe(6);
    expect(v.highest).toBe(90);
    expect(v.top.map((t) => t.studentId)).toEqual(["a", "b", "c", "d", "e"]);
  });
  it("absent child has no rank", () => {
    expect(parentTestView(rows, "g", 100).rank).toBeNull();
  });
});
