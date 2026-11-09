// Timetable, tests, marks and ranks (spec §12, §13).
// The first half is pure logic (unit tested); the second half loads data.

import "server-only";
import { adminClient } from "./supabase/admin";
import { can, visibleBatchIds, type Viewer } from "./auth";
import { allBatches, batchMap, batchShort } from "./batches";
import { boardName, type Board } from "./ids";
import type { Batch, Mark, Student, Tag, Test, TimetableEntry } from "./types";

// ---------------------------------------------------------------------------
// Pure logic
// ---------------------------------------------------------------------------

/** 42 / 50 → 84. One decimal. Null when there is no score or no max. */
export function percentOf(score: number | null | undefined, max: number | null | undefined): number | null {
  if (score === null || score === undefined || !max || Number(max) <= 0) return null;
  return Math.round((Number(score) / Number(max)) * 1000) / 10;
}

export const BANDS = ["90+", "75–89", "60–74", "Below 60"] as const;
export type Band = (typeof BANDS)[number];

export function bandOf(pct: number): Band {
  if (pct >= 90) return "90+";
  if (pct >= 75) return "75–89";
  if (pct >= 60) return "60–74";
  return "Below 60";
}

export type ScoreRow = { studentId: string; score: number | null; absent: boolean };
export type Ranked = { studentId: string; score: number; rank: number };

/**
 * Competition ranking: equal scores share a rank and the next rank skips
 * (1, 2, 2, 4). Absent students and missing scores are not ranked.
 */
export function rankScores(rows: ScoreRow[]): Ranked[] {
  const scored = rows
    .filter((r) => !r.absent && r.score !== null && r.score !== undefined)
    .map((r) => ({ studentId: r.studentId, score: Number(r.score) }))
    .sort((a, b) => b.score - a.score);
  const out: Ranked[] = [];
  scored.forEach((r, i) => {
    const rank = i > 0 && scored[i - 1].score === r.score ? out[i - 1].rank : i + 1;
    out.push({ ...r, rank });
  });
  return out;
}

export type ClassSummary = {
  appeared: number;
  absent: number;
  average: number | null; // percent
  highest: number | null; // percent
  bands: Record<Band, number>;
};

export function classSummary(rows: ScoreRow[], max: number | null): ClassSummary {
  const ranked = rankScores(rows);
  const bands = Object.fromEntries(BANDS.map((b) => [b, 0])) as Record<Band, number>;
  const pcts: number[] = [];
  for (const r of ranked) {
    const p = percentOf(r.score, max);
    if (p !== null) {
      pcts.push(p);
      bands[bandOf(p)]++;
    }
  }
  return {
    appeared: ranked.length,
    absent: rows.filter((r) => r.absent).length,
    average: pcts.length ? Math.round((pcts.reduce((a, b) => a + b, 0) / pcts.length) * 10) / 10 : null,
    highest: pcts.length ? Math.max(...pcts) : null,
    bands,
  };
}

/**
 * Dates where one class has both a School exam and a Coaching test
 * (so they can be moved apart). Key: "CB-9-2026-11-20".
 */
export function findClashes(tests: Pick<Test, "board" | "class" | "date" | "tag">[]): Set<string> {
  const tags = new Map<string, Set<Tag>>();
  for (const t of tests) {
    const k = clashKey(t);
    const set = tags.get(k) ?? new Set<Tag>();
    set.add(t.tag);
    tags.set(k, set);
  }
  return new Set([...tags].filter(([, s]) => s.size > 1).map(([k]) => k));
}

export function clashKey(t: Pick<Test, "board" | "class" | "date">): string {
  return `${t.board}-${t.class}-${t.date}`;
}

/** Is this test for this batch? (Batch tests, or whole-class tests of the batch's class.) */
export function testCoversBatch(t: Pick<Test, "batch_id" | "board" | "class">, b: Pick<Batch, "id" | "board" | "class">): boolean {
  return t.batch_id ? t.batch_id === b.id : t.board === b.board && t.class === b.class;
}

/** "08:00:00" → "08:00" for <input type="time">. */
export function timeInput(t: string | null | undefined): string {
  return t ? t.slice(0, 5) : "";
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

export type StudentLite = Pick<Student, "id" | "name" | "code" | "roll_number" | "batch_id" | "board" | "current_class">;

export async function activeStudentsOfBatches(batchIds: string[]): Promise<StudentLite[]> {
  if (!batchIds.length) return [];
  const { data } = await adminClient()
    .from("students")
    .select("id, name, code, roll_number, batch_id, board, current_class")
    .in("batch_id", batchIds)
    .eq("status", "active")
    .order("roll_number");
  return (data ?? []) as StudentLite[];
}

/** Students a test is for, limited to batches the viewer may see (null = all). */
export async function studentsForTest(test: Test, scope: string[] | null): Promise<StudentLite[]> {
  const batches = await allBatches(true);
  let ids = batches.filter((b) => testCoversBatch(test, b)).map((b) => b.id);
  if (scope) ids = ids.filter((id) => scope.includes(id));
  return activeStudentsOfBatches(ids);
}

export async function getTest(id: string): Promise<Test | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const { data } = await adminClient().from("tests").select("*").eq("id", id).maybeSingle<Test>();
  return data ?? null;
}

export async function marksOf(testIds: string[]): Promise<Mark[]> {
  if (!testIds.length) return [];
  const { data } = await adminClient().from("marks").select("test_id, student_id, score, absent").in("test_id", testIds);
  return ((data ?? []) as Mark[]).map((m) => ({ ...m, score: m.score === null ? null : Number(m.score) }));
}

/** Batches whose students' ranks this person may see. null = every batch. */
export function rankScope(viewer: Viewer): string[] | null {
  if (can(viewer, "ranks.all_batches")) return null;
  return visibleBatchIds(viewer) ?? viewer.ownBatchIds ?? [];
}

export type RankingRow = {
  rank: number;
  student: StudentLite;
  batch: string;
  score: number;
  pct: number | null;
};

export type Ranking = {
  test: Test;
  /** Ranked students the viewer may see, best first (ranks are true class ranks). */
  rows: RankingRow[];
  /** Whole-class numbers (no names). */
  summary: ClassSummary;
  limited: boolean;
};

/** Ranks for one test across everyone who took it; rows limited to what the viewer may see. */
export async function loadRanking(test: Test, viewer: Viewer): Promise<Ranking> {
  const scope = rankScope(viewer);
  const [students, marks, batches] = await Promise.all([studentsForTest(test, null), marksOf([test.id]), allBatches(true)]);
  const byId = new Map(students.map((s) => [s.id, s]));
  const rows: ScoreRow[] = marks
    .filter((m) => byId.has(m.student_id))
    .map((m) => ({ studentId: m.student_id, score: m.score, absent: m.absent }));
  const bmap = batchMap(batches);
  const ranked = rankScores(rows)
    .map((r) => {
      const s = byId.get(r.studentId)!;
      const b = s.batch_id ? bmap.get(s.batch_id) : undefined;
      return { rank: r.rank, student: s, batch: b ? batchShort(b) : "", score: r.score, pct: percentOf(r.score, test.max_marks) };
    })
    .filter((r) => scope === null || (r.student.batch_id !== null && scope.includes(r.student.batch_id)));
  return { test, rows: ranked, summary: classSummary(rows, test.max_marks), limited: scope !== null };
}

/** Past tests (with marks entered or not) the viewer may rank, newest first. */
export async function rankableTests(viewer: Viewer, today: string): Promise<Test[]> {
  const scope = rankScope(viewer);
  const { data } = await adminClient().from("tests").select("*").lte("date", today).order("date", { ascending: false }).limit(500);
  const tests = (data ?? []) as Test[];
  if (scope === null) return tests;
  const batches = (await allBatches(true)).filter((b) => scope.includes(b.id));
  return tests.filter((t) => batches.some((b) => testCoversBatch(t, b)));
}

/** Upcoming (or all from a date) tests for these batches. */
export async function testsForBatches(batches: Batch[], fromDate: string | null, limit = 200): Promise<Test[]> {
  if (!batches.length) return [];
  let q = adminClient().from("tests").select("*").order("date").order("start_time");
  if (fromDate) q = q.gte("date", fromDate);
  const classes = [...new Set(batches.map((b) => b.class))];
  q = q.in("class", classes);
  const { data } = await q.limit(limit * 4);
  return ((data ?? []) as Test[]).filter((t) => batches.some((b) => testCoversBatch(t, b))).slice(0, limit);
}

export async function timetableOf(batchIds: string[]): Promise<TimetableEntry[]> {
  if (!batchIds.length) return [];
  const { data } = await adminClient()
    .from("timetable_entries")
    .select("*")
    .in("batch_id", batchIds)
    .order("weekday")
    .order("start_time");
  return (data ?? []) as TimetableEntry[];
}

export async function facultyNames(): Promise<Map<string, string>> {
  const { data } = await adminClient().from("users").select("id, name, staff_id").eq("role", "faculty");
  return new Map(((data ?? []) as { id: string; name: string; staff_id: string }[]).map((u) => [u.id, u.name]));
}

/** "CBSE 9 · Physics unit test" */
export function testTitle(t: Pick<Test, "board" | "class" | "name">): string {
  return `${boardName(t.board as Board)} ${t.class} · ${t.name}`;
}

export type ParentTestView = {
  /** The child's rank among those who took the test; null if absent or no score. */
  rank: number | null;
  /** How many students were ranked (appeared with a score). */
  outOf: number;
  classAverage: number | null;
  highest: number | null;
  /** Top five (ties included up to rank 5), best first. */
  top: { studentId: string; score: number; rank: number }[];
};

/** What a parent sees for one test: their child's rank, class numbers and the top five. */
export function parentTestView(rows: ScoreRow[], childId: string, max: number | null): ParentTestView {
  const ranked = rankScores(rows);
  const summary = classSummary(rows, max);
  return {
    rank: ranked.find((r) => r.studentId === childId)?.rank ?? null,
    outOf: ranked.length,
    classAverage: summary.average,
    highest: summary.highest,
    top: ranked.filter((r) => r.rank <= 5),
  };
}
