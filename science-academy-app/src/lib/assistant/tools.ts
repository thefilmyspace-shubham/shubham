import "server-only";
import type Anthropic from "@anthropic-ai/sdk";
import { z } from "zod";
import { adminClient } from "../supabase/admin";
import { can, visibleBatchIds, type Viewer } from "../auth";
import { allBatches, batchLabel, batchMap } from "../batches";
import { boardName, formatMobile, parseStudentId } from "../ids";
import { addDays, monthLabel, monthStart, percent, rupees, todayIst } from "../format";
import { balanceOf, daysLate, feeStatus, FEE_STATUS_LABEL } from "../fees";
import type { Batch, Guardian, LedgerRow, Mark, Student, Test } from "../types";
import { toolAllowed, toolNamesFor, type ToolName } from "./gating";

/** A table the answer shows, with a Download PDF button. */
export type AnswerTable = { kind: "table"; title: string; columns: string[]; rows: string[][] };

/** What the tools leave behind for the answer (a table, a proposed action). */
export type ToolContext = { table: AnswerTable | null; actionId: string | null };

type Def = { description: string; schema: z.ZodObject<z.ZodRawShape> };

const boardSchema = z.enum(["CB", "MP"]).optional().describe("CB = CBSE, MP = MP Board");
const classSchema = z.number().int().min(6).max(12).optional();

const DEFS: Record<ToolName, Def> = {
  list_batches: {
    description: "List the batches this person may see (board, class, name, time, id). Use to turn 'class 10 PCB' into a batch id.",
    schema: z.object({ board: boardSchema, class: classSchema }),
  },
  find_student: {
    description: "Find students by student ID (current or earlier, e.g. MP9-025-26), name, or class. Returns id, name, current ID, class, board, batch.",
    schema: z.object({ query: z.string().min(1).describe("ID, name or part of a name"), board: boardSchema, class: classSchema }),
  },
  student_attendance: {
    description: "Attendance of one student for a month: present / absent / late counts, percentage, absent dates.",
    schema: z.object({ student_id: z.string().uuid(), month: z.string().regex(/^\d{4}-\d{2}$/).optional().describe("YYYY-MM, default this month") }),
  },
  student_marks: {
    description: "Recent test marks of one student (test, date, School/Coaching tag, score, percentage).",
    schema: z.object({ student_id: z.string().uuid(), limit: z.number().int().min(1).max(30).optional() }),
  },
  batch_attendance_summary: {
    description: "Attendance of batches on one date: present, absent, late, not marked.",
    schema: z.object({ date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().describe("YYYY-MM-DD, default today"), batch_id: z.string().uuid().optional() }),
  },
  low_attendance: {
    description: "Students below a percentage of attendance (default 75%) in the last N days (default 30).",
    schema: z.object({ below: z.number().min(1).max(100).optional(), days: z.number().int().min(7).max(120).optional(), board: boardSchema, class: classSchema }),
  },
  list_tests: {
    description: "Tests and exams (with ids), newest first, optionally for a board and class.",
    schema: z.object({ board: boardSchema, class: classSchema, limit: z.number().int().min(1).max(30).optional() }),
  },
  test_results: {
    description: "Marks of every student in one test, ranked, optionally for one batch.",
    schema: z.object({ test_id: z.string().uuid(), batch_id: z.string().uuid().optional() }),
  },
  compare_batches: {
    description: "Compare the marks of two or more batches in one test (appeared, average, highest, lowest). The comparison is shown as a table with a PDF download.",
    schema: z.object({ test_id: z.string().uuid(), batch_ids: z.array(z.string().uuid()).min(2).max(6) }),
  },
  class_toppers: {
    description: "Top 5 of a class in a test (latest test of the class if no test id).",
    schema: z.object({ board: z.enum(["CB", "MP"]), class: z.number().int().min(6).max(12), test_id: z.string().uuid().optional() }),
  },
  student_contacts: {
    description: "Parents' / guardians' phone numbers of one student, and which one is the login number.",
    schema: z.object({ student_id: z.string().uuid() }),
  },
  fee_status: {
    description: "Fee status of one student for the last 6 months: amount, paid, balance, status.",
    schema: z.object({ student_id: z.string().uuid() }),
  },
  overdue_list: {
    description: "Students with fees overdue for a month (default this month), longest late first, with balance.",
    schema: z.object({ month: z.string().regex(/^\d{4}-\d{2}$/).optional(), board: boardSchema, class: classSchema }),
  },
  propose_fee_reminders: {
    description:
      "PROPOSE (never sends) private fee reminders to the parents of overdue students for a month, optionally one board/class or given students. Admin sees a confirm card and decides.",
    schema: z.object({
      month: z.string().regex(/^\d{4}-\d{2}$/).optional(),
      board: boardSchema,
      class: classSchema,
      student_ids: z.array(z.string().uuid()).max(200).optional(),
    }),
  },
};

/** The tool definitions this person gets (Anthropic format). */
export function toolsFor(viewer: Viewer): Anthropic.Tool[] {
  return toolNamesFor(viewer.perms).map((name) => ({
    name,
    description: DEFS[name].description,
    input_schema: z.toJSONSchema(DEFS[name].schema) as Anthropic.Tool.InputSchema,
  }));
}

type Result = { content: string; isError: boolean };
const ok = (data: unknown): Result => ({ content: JSON.stringify(data), isError: false });
const fail = (msg: string): Result => ({ content: msg, isError: true });

/** Batches whose students this person may see (null = all). */
function studentScope(viewer: Viewer): string[] | null {
  return visibleBatchIds(viewer);
}

/** Batches whose ranks this person may see (null = all). */
function rankScope(viewer: Viewer): string[] | null {
  if (can(viewer, "ranks.all_batches")) return null;
  return visibleBatchIds(viewer) ?? [];
}

function inScope(scope: string[] | null, batchId: string | null): boolean {
  return scope === null || (batchId !== null && scope.includes(batchId));
}

async function loadStudent(viewer: Viewer, id: string): Promise<Student | null> {
  const { data } = await adminClient().from("students").select("*").eq("id", id).neq("status", "draft").maybeSingle<Student>();
  if (!data || !inScope(studentScope(viewer), data.batch_id)) return null;
  return data;
}

const NOT_FOUND = "No such student, or this login cannot see them.";

function monthRange(month?: string): { start: string; end: string } {
  const start = month ? `${month}-01` : monthStart(todayIst());
  const [y, m] = start.split("-").map(Number);
  const next = m === 12 ? `${y + 1}-01-01` : `${y}-${String(m + 1).padStart(2, "0")}-01`;
  return { start, end: addDays(next, -1) };
}

function scoreText(mark: Mark | undefined, test: Test): string {
  if (!mark) return "no mark";
  if (mark.absent) return "absent";
  return test.max_marks ? `${mark.score}/${test.max_marks}` : String(mark.score);
}

function pct(mark: Mark | undefined, test: Test): number | null {
  if (!mark || mark.absent || mark.score === null || !test.max_marks) return null;
  return Math.round((Number(mark.score) / Number(test.max_marks)) * 1000) / 10;
}

/** Runs one tool for this person. Checks the permission again before touching data. */
export async function runTool(viewer: Viewer, name: string, input: unknown, ctx: ToolContext): Promise<Result> {
  if (!(name in DEFS) || !toolAllowed(name as ToolName, viewer.perms)) return fail("This tool is not available for this login.");
  const parsed = DEFS[name as ToolName].schema.safeParse(input ?? {});
  if (!parsed.success) return fail(`Bad input: ${parsed.error.message}`);
  const args = parsed.data as Record<string, never>;
  try {
    return await TOOLS[name as ToolName](viewer, args, ctx);
  } catch (err) {
    console.error("assistant tool failed", name, err);
    return fail("Could not read this data right now.");
  }
}

type Impl = (viewer: Viewer, args: Record<string, unknown>, ctx: ToolContext) => Promise<Result>;

const TOOLS: Record<ToolName, Impl> = {
  async list_batches(viewer, a) {
    const scope = studentScope(viewer);
    const list = (await allBatches()).filter(
      (b) => inScope(scope, b.id) && (!a.board || b.board === a.board) && (!a.class || b.class === a.class),
    );
    return ok(list.map((b) => ({ id: b.id, label: batchLabel(b) })));
  },

  async find_student(viewer, a) {
    const db = adminClient();
    const query = String(a.query).trim();
    const scope = studentScope(viewer);
    let ids: string[] | null = null;
    if (parseStudentId(query)) {
      const code = query.replace(/\s+/g, "").toUpperCase();
      const { data } = await db.from("student_id_history").select("student_id").eq("code", code);
      const fromHistory = ((data ?? []) as { student_id: string }[]).map((r) => r.student_id);
      const { data: current } = await db.from("students").select("id").eq("code", code);
      ids = [...new Set([...fromHistory, ...((current ?? []) as { id: string }[]).map((r) => r.id)])];
      if (!ids.length) return ok({ found: 0, note: `No student with ID ${code}.` });
    }
    let q = db.from("students").select("*").neq("status", "draft").limit(15);
    if (ids) q = q.in("id", ids);
    else q = q.ilike("name", `%${query.replace(/[%_]/g, "")}%`);
    if (a.board) q = q.eq("board", a.board as string);
    if (a.class) q = q.eq("current_class", a.class as number);
    const { data } = await q;
    const batches = batchMap(await allBatches(true));
    const list = ((data ?? []) as Student[]).filter((s) => inScope(scope, s.batch_id));
    if (!list.length) return ok({ found: 0, note: "No matching student this login can see." });
    return ok({
      found: list.length,
      students: list.map((s) => ({
        id: s.id,
        name: s.name,
        id_code: s.code,
        class: s.current_class,
        board: boardName(s.board),
        batch: s.batch_id && batches.get(s.batch_id) ? batchLabel(batches.get(s.batch_id)!) : null,
        status: s.status,
      })),
    });
  },

  async student_attendance(viewer, a) {
    const s = await loadStudent(viewer, String(a.student_id));
    if (!s) return fail(NOT_FOUND);
    const { start, end } = monthRange(a.month as string | undefined);
    const { data } = await adminClient()
      .from("attendance")
      .select("date, status")
      .eq("student_id", s.id)
      .gte("date", start)
      .lte("date", end)
      .order("date");
    const rows = (data ?? []) as { date: string; status: "P" | "A" | "L" }[];
    const count = (st: string) => rows.filter((r) => r.status === st).length;
    const present = count("P") + count("L");
    return ok({
      student: `${s.name} (${s.code})`,
      month: monthLabel(start),
      days_marked: rows.length,
      present: count("P"),
      late: count("L"),
      absent: count("A"),
      attendance_percent: rows.length ? percent(present, rows.length) : null,
      absent_dates: rows.filter((r) => r.status === "A").map((r) => r.date),
    });
  },

  async student_marks(viewer, a) {
    const s = await loadStudent(viewer, String(a.student_id));
    if (!s) return fail(NOT_FOUND);
    const db = adminClient();
    const { data: marks } = await db.from("marks").select("*").eq("student_id", s.id);
    const list = (marks ?? []) as Mark[];
    if (!list.length) return ok({ student: `${s.name} (${s.code})`, tests: [], note: "No marks entered yet." });
    const { data: tests } = await db
      .from("tests")
      .select("*")
      .in("id", list.map((m) => m.test_id))
      .order("date", { ascending: false })
      .limit(Number(a.limit ?? 10));
    return ok({
      student: `${s.name} (${s.code})`,
      tests: ((tests ?? []) as Test[]).map((t) => {
        const m = list.find((x) => x.test_id === t.id);
        return { test: t.name, subject: t.subject, date: t.date, tag: t.tag, score: scoreText(m, t), percent: pct(m, t) };
      }),
    });
  },

  async batch_attendance_summary(viewer, a) {
    const date = (a.date as string | undefined) ?? todayIst();
    const scope = studentScope(viewer);
    const batches = (await allBatches()).filter((b) => inScope(scope, b.id) && (!a.batch_id || b.id === a.batch_id));
    if (!batches.length) return ok({ note: "No batch this login can see." });
    const db = adminClient();
    const ids = batches.map((b) => b.id);
    const [{ data: students }, { data: att }] = await Promise.all([
      db.from("students").select("id, batch_id").in("batch_id", ids).eq("status", "active"),
      db.from("attendance").select("batch_id, status").in("batch_id", ids).eq("date", date),
    ]);
    const st = (students ?? []) as { id: string; batch_id: string }[];
    const at = (att ?? []) as { batch_id: string; status: string }[];
    return ok({
      date,
      batches: batches.map((b) => {
        const mine = at.filter((r) => r.batch_id === b.id);
        const total = st.filter((s) => s.batch_id === b.id).length;
        return {
          batch: batchLabel(b),
          students: total,
          marked: mine.length > 0,
          present: mine.filter((r) => r.status === "P").length,
          late: mine.filter((r) => r.status === "L").length,
          absent: mine.filter((r) => r.status === "A").length,
        };
      }),
    });
  },

  async low_attendance(viewer, a) {
    const below = Number(a.below ?? 75);
    const days = Number(a.days ?? 30);
    const today = todayIst();
    const from = addDays(today, -days);
    const db = adminClient();
    const scope = studentScope(viewer);
    let q = db.from("students").select("id, name, code, batch_id, board, current_class").eq("status", "active");
    if (a.board) q = q.eq("board", a.board as string);
    if (a.class) q = q.eq("current_class", a.class as number);
    const { data: students } = await q;
    const list = ((students ?? []) as Student[]).filter((s) => inScope(scope, s.batch_id));
    if (!list.length) return ok({ note: "No students this login can see." });
    const { data: att } = await db
      .from("attendance")
      .select("student_id, status")
      .in("student_id", list.map((s) => s.id))
      .gte("date", from)
      .lte("date", today);
    const rows = (att ?? []) as { student_id: string; status: string }[];
    const out = list
      .map((s) => {
        const mine = rows.filter((r) => r.student_id === s.id);
        const present = mine.filter((r) => r.status !== "A").length;
        return { name: s.name, id_code: s.code, days_marked: mine.length, percent: mine.length ? percent(present, mine.length) : null };
      })
      .filter((r) => r.percent !== null && r.percent < below)
      .sort((x, y) => (x.percent ?? 0) - (y.percent ?? 0));
    return ok({ from, to: today, below_percent: below, students: out });
  },

  async list_tests(_viewer, a) {
    let q = adminClient().from("tests").select("*").order("date", { ascending: false }).limit(Number(a.limit ?? 15));
    if (a.board) q = q.eq("board", a.board as string);
    if (a.class) q = q.eq("class", a.class as number);
    const { data } = await q;
    return ok(
      ((data ?? []) as Test[]).map((t) => ({
        id: t.id,
        name: t.name,
        subject: t.subject,
        date: t.date,
        tag: t.tag,
        class: `${boardName(t.board)} ${t.class}`,
        max_marks: t.max_marks,
      })),
    );
  },

  async test_results(viewer, a) {
    const r = await resultsOf(viewer, String(a.test_id), a.batch_id ? [String(a.batch_id)] : null);
    if ("error" in r) return fail(r.error);
    return ok({
      test: r.test.name,
      date: r.test.date,
      max_marks: r.test.max_marks,
      results: r.rows.map((x, i) => ({ rank: x.absent ? null : i + 1, name: x.student.name, id_code: x.student.code, batch: x.batch, score: x.text, percent: x.pct })),
    });
  },

  async compare_batches(viewer, a, ctx) {
    const ids = (a.batch_ids as string[]) ?? [];
    const r = await resultsOf(viewer, String(a.test_id), ids);
    if ("error" in r) return fail(r.error);
    const batches = batchMap(await allBatches(true));
    const summary = ids.map((id) => {
      const b = batches.get(id);
      const mine = r.rows.filter((x) => x.student.batch_id === id && !x.absent && x.score !== null);
      const scores = mine.map((x) => Number(x.score));
      const avg = scores.length ? scores.reduce((s, v) => s + v, 0) / scores.length : null;
      return {
        batch: b ? batchLabel(b) : "Unknown batch",
        appeared: scores.length,
        absent: r.rows.filter((x) => x.student.batch_id === id && x.absent).length,
        average: avg === null ? null : Math.round(avg * 10) / 10,
        highest: scores.length ? Math.max(...scores) : null,
        lowest: scores.length ? Math.min(...scores) : null,
      };
    });
    const max = r.test.max_marks ? ` / ${r.test.max_marks}` : "";
    ctx.table = {
      kind: "table",
      title: `${r.test.name} (${r.test.date}): batch comparison`,
      columns: ["Batch", "Appeared", "Absent", "Average", "Highest", "Lowest"],
      rows: summary.map((s) => [
        s.batch,
        String(s.appeared),
        String(s.absent),
        s.average === null ? "-" : `${s.average}${max}`,
        s.highest === null ? "-" : String(s.highest),
        s.lowest === null ? "-" : String(s.lowest),
      ]),
    };
    return ok({ test: r.test.name, max_marks: r.test.max_marks, batches: summary, note: "A table with a PDF download is shown to the user." });
  },

  async class_toppers(viewer, a) {
    const db = adminClient();
    let testId = a.test_id as string | undefined;
    if (!testId) {
      const { data } = await db
        .from("tests")
        .select("id")
        .eq("board", a.board as string)
        .eq("class", a.class as number)
        .lte("date", todayIst())
        .order("date", { ascending: false })
        .limit(1)
        .maybeSingle<{ id: string }>();
      if (!data) return ok({ note: "No test found for this class." });
      testId = data.id;
    }
    const r = await resultsOf(viewer, testId, null);
    if ("error" in r) return fail(r.error);
    const top = r.rows.filter((x) => !x.absent && x.score !== null).slice(0, 5);
    return ok({
      test: r.test.name,
      date: r.test.date,
      max_marks: r.test.max_marks,
      top5: top.map((x, i) => ({ rank: i + 1, name: x.student.name, id_code: x.student.code, batch: x.batch, score: x.text, percent: x.pct })),
    });
  },

  async student_contacts(viewer, a) {
    const s = await loadStudent(viewer, String(a.student_id));
    if (!s) return fail(NOT_FOUND);
    const { data } = await adminClient().from("guardians").select("*").eq("student_id", s.id);
    return ok({
      student: `${s.name} (${s.code})`,
      contacts: ((data ?? []) as Guardian[]).map((g) => ({
        relation: g.relation,
        name: g.name,
        mobile: formatMobile(g.mobile),
        login_number: g.is_login_number,
      })),
    });
  },

  async fee_status(viewer, a) {
    const s = await loadStudent(viewer, String(a.student_id));
    if (!s) return fail(NOT_FOUND);
    const today = todayIst();
    const { data } = await adminClient()
      .from("fees_ledger")
      .select("*")
      .eq("student_id", s.id)
      .order("month", { ascending: false })
      .limit(6);
    const rows = (data ?? []) as LedgerRow[];
    return ok({
      student: `${s.name} (${s.code})`,
      monthly_fee: rupees(s.monthly_fee),
      months: rows.map((r) => ({
        month: monthLabel(r.month),
        amount: rupees(r.amount),
        paid: rupees(r.paid),
        balance: rupees(balanceOf(r)),
        status: FEE_STATUS_LABEL[feeStatus(r.amount, r.paid, r.month, today, r.due_date)],
      })),
    });
  },

  async overdue_list(viewer, a) {
    const list = await overdueFor(viewer, a.month as string | undefined, a.board as string | undefined, a.class as number | undefined);
    return ok({
      month: monthLabel(list.month),
      count: list.items.length,
      total_balance: rupees(list.items.reduce((s, x) => s + x.balance, 0)),
      students: list.items.slice(0, 60).map((x) => ({ name: x.student.name, id_code: x.student.code, class: x.student.current_class, balance: rupees(x.balance), days_late: x.daysLate })),
    });
  },

  async propose_fee_reminders(viewer, a, ctx) {
    const list = await overdueFor(viewer, a.month as string | undefined, a.board as string | undefined, a.class as number | undefined);
    let items = list.items;
    const wanted = a.student_ids as string[] | undefined;
    if (wanted?.length) items = items.filter((x) => wanted.includes(x.student.id));
    if (!items.length) return ok({ note: "Nobody to remind: no overdue fees matched." });
    const total = items.reduce((s, x) => s + x.balance, 0);
    const summary = `Fee reminders for ${monthLabel(list.month)}: ${items.length} ${items.length === 1 ? "parent" : "parents"}, ${rupees(total)}`;
    const { data, error } = await adminClient()
      .from("ai_actions")
      .insert({
        requested_by: viewer.user.id,
        kind: "send_fee_reminders",
        summary,
        payload: {
          month: list.month,
          total,
          students: items.map((x) => ({ id: x.student.id, name: x.student.name, code: x.student.code, balance: x.balance })),
        },
      })
      .select("id")
      .single<{ id: string }>();
    if (error || !data) return fail("Could not prepare the reminders.");
    ctx.actionId = data.id;
    return ok({ proposed: true, parents: items.length, total: rupees(total), note: "Nothing is sent yet. The admin sees a confirm card and decides." });
  },
};

type ResultRow = { student: Student; batch: string | null; score: number | null; absent: boolean; text: string; pct: number | null };

async function resultsOf(viewer: Viewer, testId: string, batchIds: string[] | null): Promise<{ test: Test; rows: ResultRow[] } | { error: string }> {
  const db = adminClient();
  const { data: test } = await db.from("tests").select("*").eq("id", testId).maybeSingle<Test>();
  if (!test) return { error: "No such test." };
  const scope = rankScope(viewer);
  if (batchIds && batchIds.some((id) => !inScope(scope, id))) return { error: "This login cannot see one of these batches." };
  const { data: marks } = await db.from("marks").select("*").eq("test_id", test.id);
  const list = (marks ?? []) as Mark[];
  if (!list.length) return { error: "No marks entered for this test yet." };
  const { data: students } = await db.from("students").select("*").in("id", list.map((m) => m.student_id));
  const batches = batchMap(await allBatches(true));
  const rows = ((students ?? []) as Student[])
    .filter((s) => inScope(scope, s.batch_id) && (!batchIds || (s.batch_id !== null && batchIds.includes(s.batch_id))))
    .map((s) => {
      const m = list.find((x) => x.student_id === s.id)!;
      const b: Batch | undefined = s.batch_id ? batches.get(s.batch_id) : undefined;
      return { student: s, batch: b ? batchLabel(b) : null, score: m.score === null ? null : Number(m.score), absent: m.absent, text: scoreText(m, test), pct: pct(m, test) };
    })
    .sort((x, y) => Number(x.absent) - Number(y.absent) || (y.score ?? -1) - (x.score ?? -1));
  if (!rows.length) return { error: "No results this login can see for this test." };
  return { test, rows };
}

async function overdueFor(viewer: Viewer, month: string | undefined, board?: string, cls?: number) {
  const today = todayIst();
  const m = month ? `${month}-01` : monthStart(today);
  const db = adminClient();
  const { data: ledger } = await db.from("fees_ledger").select("*").eq("month", m);
  const rows = ((ledger ?? []) as LedgerRow[]).filter((r) => feeStatus(r.amount, r.paid, r.month, today, r.due_date) === "overdue");
  if (!rows.length) return { month: m, items: [] as { student: Student; balance: number; daysLate: number }[] };
  const { data: students } = await db.from("students").select("*").in("id", rows.map((r) => r.student_id)).eq("status", "active");
  const scope = studentScope(viewer);
  const byId = new Map(((students ?? []) as Student[]).map((s) => [s.id, s]));
  const items = rows
    .map((r) => ({ student: byId.get(r.student_id), balance: balanceOf(r), daysLate: daysLate(r.month, today, r.due_date) }))
    .filter((x): x is { student: Student; balance: number; daysLate: number } => Boolean(x.student))
    .filter((x) => inScope(scope, x.student.batch_id) && (!board || x.student.board === board) && (!cls || x.student.current_class === cls))
    .sort((x, y) => y.daysLate - x.daysLate || y.balance - x.balance);
  return { month: m, items };
}
