import { ChevronDown, Medal, Trophy } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { dateLabel } from "@/lib/format";
import { allBatches } from "@/lib/batches";
import { parentTestView, percentOf, testCoversBatch, type ParentTestView, type ScoreRow } from "@/lib/academics";
import type { Test } from "@/lib/types";
import { ChildStrip } from "@/components/ChildStrip";
import { Card, Chip, Empty } from "@/components/ui";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Marks & ranks" };

type TestRow = Pick<Test, "id" | "name" | "subject" | "date" | "tag" | "max_marks" | "board" | "class" | "batch_id">;

/**
 * The child's test marks with their rank in class, the class average and the
 * top five for each test (own child only; other students appear only in the
 * top-five list, by name and score).
 */
export default async function ParentMarksPage() {
  const { children, child } = await parentContext();
  const { t } = await getT();
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty>{t("academics.noStudentLinked")}</Empty>
      </div>
    );
  }
  const db = adminClient();
  const { data } = await db
    .from("marks")
    .select("score, absent, tests!inner(id, name, subject, date, tag, max_marks, board, class, batch_id)")
    .eq("student_id", child.id);
  type Row = { score: number | null; absent: boolean; tests: TestRow };
  const rows = ((data ?? []) as unknown as Row[]).sort((a, b) => b.tests.date.localeCompare(a.tests.date));

  // Everyone who took the same tests: classmates of the child's board and class.
  const testIds = rows.map((r) => r.tests.id);
  const [{ data: classmates }, { data: allMarks }, batches] = await Promise.all([
    db.from("students").select("id, name, batch_id").eq("board", child.board).eq("current_class", child.current_class).eq("status", "active"),
    testIds.length
      ? db.from("marks").select("test_id, student_id, score, absent").in("test_id", testIds)
      : Promise.resolve({ data: [] as { test_id: string; student_id: string; score: number | null; absent: boolean }[] }),
    allBatches(true),
  ]);
  const mates = (classmates ?? []) as { id: string; name: string; batch_id: string | null }[];
  const names = new Map(mates.map((s) => [s.id, s.name]));
  const marksByTest = new Map<string, ScoreRow[]>();
  for (const m of (allMarks ?? []) as { test_id: string; student_id: string; score: number | null; absent: boolean }[]) {
    if (!marksByTest.has(m.test_id)) marksByTest.set(m.test_id, []);
    marksByTest.get(m.test_id)!.push({ studentId: m.student_id, score: m.score === null ? null : Number(m.score), absent: m.absent });
  }
  const views = new Map<string, ParentTestView>();
  for (const r of rows) {
    const covered = new Set(batches.filter((b) => testCoversBatch(r.tests, b)).map((b) => b.id));
    const takers = (marksByTest.get(r.tests.id) ?? []).filter((m) => {
      const s = mates.find((x) => x.id === m.studentId);
      return s && s.batch_id !== null && covered.has(s.batch_id);
    });
    views.set(r.tests.id, parentTestView(takers, child.id, r.tests.max_marks ? Number(r.tests.max_marks) : null));
  }

  const pcts = rows.map((r) => (r.absent ? null : percentOf(r.score, r.tests.max_marks))).filter((p): p is number => p !== null);
  const avg = pcts.length ? Math.round((pcts.reduce((a, b) => a + b, 0) / pcts.length) * 10) / 10 : null;
  const latest = rows.find((r) => views.get(r.tests.id)?.rank);
  const latestView = latest ? views.get(latest.tests.id) : undefined;

  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent/marks" />
      <div className="mx-auto max-w-lg px-4 pt-4">
        <div className="mb-3 flex items-baseline justify-between">
          <h1 className="text-xl font-extrabold text-navy">{t("academics.pm.title")}</h1>
          {avg !== null && <Chip tone="navy">{t("academics.marks.average", { n: avg })}</Chip>}
        </div>

        {latest && latestView?.rank && (
          <Card className="mb-4 flex items-center gap-4 p-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-primary-soft text-primary">
              <Medal size={26} />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-muted">{t("academics.pm.latestTest", { name: latest.tests.name })}</p>
              <p className="text-2xl font-extrabold text-navy">
                {t("academics.pm.rank", { r: latestView.rank })} <span className="text-base font-semibold text-muted">{t("academics.pm.of", { n: latestView.outOf })}</span>
              </p>
              <p className="text-xs text-muted">
                {t("academics.class", { n: child.current_class })}
                {latestView.classAverage !== null ? t("academics.pm.classAvg", { n: latestView.classAverage }) : ""}
              </p>
            </div>
          </Card>
        )}

        {rows.length === 0 ? (
          <Empty icon={Trophy}>{t("academics.pm.noMarks")}</Empty>
        ) : (
          <Card className="divide-y divide-line overflow-hidden">
            {rows.map((r) => {
              const pct = r.absent ? null : percentOf(r.score, r.tests.max_marks);
              const v = views.get(r.tests.id);
              return (
                <details key={r.tests.id} className="group">
                  <summary className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-field">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-bold">{r.tests.name}</p>
                      <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
                        {dateLabel(r.tests.date)}
                        {r.tests.subject ? ` · ${r.tests.subject}` : ""}
                        <Chip tone={r.tests.tag === "School" ? "violet" : "primary"}>{t(r.tests.tag === "School" ? "academics.tag.School" : "academics.tag.Coaching")}</Chip>
                        {v?.rank ? <Chip tone="ok">{t("academics.pm.rankChip", { r: v.rank, n: v.outOf })}</Chip> : null}
                      </p>
                    </div>
                    <div className="text-right">
                      {r.absent ? (
                        <Chip tone="danger">{t("academics.absent")}</Chip>
                      ) : (
                        <>
                          <p className="font-extrabold text-navy">
                            {Number(r.score)}
                            {r.tests.max_marks ? <span className="text-xs font-semibold text-muted"> / {Number(r.tests.max_marks)}</span> : null}
                          </p>
                          {pct !== null && <p className={`text-xs font-bold ${pct >= 75 ? "text-ok" : pct >= 60 ? "text-warn" : "text-danger"}`}>{pct}%</p>}
                        </>
                      )}
                    </div>
                    <ChevronDown size={16} className="shrink-0 text-faint transition-transform group-open:rotate-180" />
                  </summary>
                  {v && v.outOf > 0 && (
                    <div className="bg-field/60 px-4 pt-2 pb-3">
                      <p className="mb-1.5 text-[12px] font-semibold text-muted">
                        {t("academics.pm.appeared", { n: v.outOf })}
                        {v.classAverage !== null ? t("academics.pm.classAvg", { n: v.classAverage }) : ""}
                        {v.highest !== null ? t("academics.pm.highest", { n: v.highest }) : ""}
                      </p>
                      <p className="mb-1 text-[12px] font-bold text-navy">{t("academics.pm.top5")}</p>
                      <ol className="space-y-1">
                        {v.top.map((x) => {
                          const me = x.studentId === child.id;
                          return (
                            <li key={x.studentId} className={`flex items-center gap-2 rounded-field px-2 py-1 text-[13px] ${me ? "bg-primary-soft font-bold text-primary" : ""}`}>
                              <span className="w-5 text-center font-extrabold">{x.rank}</span>
                              <span className="min-w-0 flex-1 truncate">{me ? t("academics.pm.yourChild", { name: names.get(x.studentId) ?? child.name }) : (names.get(x.studentId) ?? t("academics.pm.student"))}</span>
                              <span className="font-semibold">
                                {x.score}
                                {r.tests.max_marks ? `/${Number(r.tests.max_marks)}` : ""}
                              </span>
                            </li>
                          );
                        })}
                      </ol>
                    </div>
                  )}
                </details>
              );
            })}
          </Card>
        )}
        <p className="mt-3 text-center text-[11.5px] text-muted">{t("academics.pm.tapHint")}</p>
      </div>
    </>
  );
}
