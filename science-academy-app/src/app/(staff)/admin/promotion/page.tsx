import { ArrowRight, CheckCircle2, GraduationCap, TriangleAlert } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { allBatches, batchShort } from "@/lib/batches";
import { boardName, formatStudentId, sessionLabel, type Board } from "@/lib/ids";
import type { Student } from "@/lib/types";
import { Banner, Card, Empty, Page, PageHeader, Section } from "@/components/ui";
import { promoteClass } from "./actions";

export const metadata = { title: "Year-end promotion" };

type Search = { board?: string; class?: string; batch?: string; session?: string; done?: string; passed?: string; error?: string };

export default async function PromotionPage({ searchParams }: { searchParams: Promise<Search> }) {
  await requirePermission("admin.promotion");
  const sp = await searchParams;
  const board = sp.board === "CB" || sp.board === "MP" ? (sp.board as Board) : null;
  const cls = sp.class && /^(6|7|8|9|10|11|12)$/.test(sp.class) ? Number(sp.class) : null;
  const batches = await allBatches();
  const classBatches = batches.filter((b) => b.board === board && b.class === cls);
  const nextBatches = batches.filter((b) => b.board === board && b.class === (cls ?? 0) + 1);
  const batch = sp.batch && classBatches.some((b) => b.id === sp.batch) ? sp.batch : null;

  let students: Student[] = [];
  let sessions: number[] = [];
  if (board && cls) {
    let q = adminClient().from("students").select("*").eq("status", "active").eq("board", board).eq("current_class", cls);
    if (batch) q = q.eq("batch_id", batch);
    const { data } = await q.order("roll_number");
    const all = (data ?? []) as Student[];
    sessions = [...new Set(all.map((s) => s.session_year))].sort((a, b) => a - b);
    const session = sp.session && sessions.includes(Number(sp.session)) ? Number(sp.session) : sessions[0];
    students = all.filter((s) => s.session_year === session);
  }
  const fromSession = students[0]?.session_year ?? null;
  const batchName = new Map(batches.map((b) => [b.id, batchShort(b)]));

  return (
    <>
      <PageHeader title="Year-end promotion" subtitle="Admin only · moves a whole class up and updates the IDs" />
      <Page>
        {sp.done !== undefined && (
          <Banner tone="ok" icon={CheckCircle2}>
            Done: {sp.done} promoted{Number(sp.passed) ? `, ${sp.passed} passed out` : ""}. Old IDs still work in search and show as “Earlier ID”.
          </Banner>
        )}
        {sp.error === "confirm" && <Banner tone="danger">Tick the confirm box to run the promotion.</Banner>}
        {sp.error === "batch" && <Banner tone="danger">The new batch must be in the next class of the same board.</Banner>}

        <Section title="1. Choose the class">
          <Card className="p-4">
            <form className="grid grid-cols-1 gap-3 sm:grid-cols-4" method="get">
              <div>
                <label className="label" htmlFor="board">
                  Board
                </label>
                <select id="board" name="board" className="field" defaultValue={board ?? ""}>
                  <option value="">Choose</option>
                  <option value="CB">CBSE</option>
                  <option value="MP">MP Board</option>
                </select>
              </div>
              <div>
                <label className="label" htmlFor="class">
                  Class
                </label>
                <select id="class" name="class" className="field" defaultValue={cls ?? ""}>
                  <option value="">Choose</option>
                  {[6, 7, 8, 9, 10, 11, 12].map((c) => (
                    <option key={c} value={c}>
                      Class {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="batch">
                  Batch (optional)
                </label>
                <select id="batch" name="batch" className="field" defaultValue={batch ?? ""}>
                  <option value="">Whole class</option>
                  {classBatches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {batchShort(b)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button className="btn btn-soft w-full">Show students</button>
              </div>
            </form>
            {sessions.length > 1 && (
              <p className="mt-3 text-xs text-muted">
                Students from more than one session are in this class. Showing session {fromSession !== null ? sessionLabel(fromSession) : ""}. Others:{" "}
                {sessions
                  .filter((s) => s !== fromSession)
                  .map((s) => (
                    <a key={s} className="font-bold text-primary" href={`?board=${board}&class=${cls}${batch ? `&batch=${batch}` : ""}&session=${s}`}>
                      {sessionLabel(s)}{" "}
                    </a>
                  ))}
              </p>
            )}
            <p className="mt-3 text-xs text-muted">Tip: promote the highest class first (12, then 11, then 10 …).</p>
          </Card>
        </Section>

        {board && cls && (
          <Section title={`2. Check: ${boardName(board)} Class ${cls}${cls < 12 ? ` → Class ${cls + 1}` : " → passed out"}`}>
            {!students.length ? (
              <Empty icon={GraduationCap}>No active students to promote here.</Empty>
            ) : (
              <>
                <Card className="max-h-[420px] divide-y divide-line overflow-y-auto">
                  {students.map((s) => (
                    <div key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm">
                      <span className="min-w-0 flex-1 font-semibold">{s.name}</span>
                      <span className="text-xs text-muted">{s.batch_id ? batchName.get(s.batch_id) : "No batch"}</span>
                      <span className="font-mono text-[12.5px]">{s.code}</span>
                      <ArrowRight size={14} className="text-faint" />
                      <span className="font-mono text-[12.5px] font-bold text-green">
                        {cls < 12 ? formatStudentId(s.board, cls + 1, s.roll_number!, s.session_year + 1) : "Passed out"}
                      </span>
                    </div>
                  ))}
                </Card>

                <Section title="3. Confirm">
                  <Card className="p-4">
                    <form action={promoteClass} className="space-y-3">
                      <input type="hidden" name="board" value={board} />
                      <input type="hidden" name="class" value={cls} />
                      <input type="hidden" name="from_session" value={fromSession ?? ""} />
                      {batch && <input type="hidden" name="batch" value={batch} />}
                      {cls < 12 && (
                        <div>
                          <label className="label" htmlFor="target_batch">
                            New batch in Class {cls + 1}
                          </label>
                          <select id="target_batch" name="target_batch" className="field" defaultValue="">
                            <option value="">No batch yet (set later)</option>
                            {nextBatches.map((b) => (
                              <option key={b.id} value={b.id}>
                                {batchShort(b)}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <Banner tone="warn" icon={TriangleAlert}>
                        {cls < 12
                          ? `${students.length} students move to Class ${cls + 1}, session ${sessionLabel((fromSession ?? 0) + 1)}. Roll numbers stay. Old bills keep the old ID.`
                          : `${students.length} students will be marked as passed out.`}
                      </Banner>
                      <label className="flex items-center gap-2 text-sm font-semibold">
                        <input type="checkbox" name="confirm" className="h-4 w-4 accent-[var(--color-primary)]" /> I have checked the list
                      </label>
                      <button className="btn btn-primary w-full sm:w-auto">
                        <GraduationCap size={16} /> Promote {students.length} students
                      </button>
                    </form>
                  </Card>
                </Section>
              </>
            )}
          </Section>
        )}
      </Page>
    </>
  );
}
