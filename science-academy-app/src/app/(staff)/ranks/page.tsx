import Link from "next/link";
import { Download, Medal, Trophy } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { BOARDS, boardName } from "@/lib/ids";
import { dateLabel, todayIst } from "@/lib/format";
import { BANDS, loadRanking, marksOf, rankableTests, type Ranking } from "@/lib/academics";
import type { Test } from "@/lib/types";
import { Meter } from "@/components/BarChart";
import { Card, Chip, Empty, FilterChips, Page, PageHeader, Section, Stat } from "@/components/ui";

export const metadata = { title: "Ranks" };

type SP = { board?: string; class?: string; test?: string };

export default async function RanksPage({ searchParams }: { searchParams: Promise<SP> }) {
  const viewer = await requirePermission("ranks.view");
  const sp = await searchParams;
  const today = todayIst();
  const tests = await rankableTests(viewer, today);

  const requested = tests.find((t) => t.id === sp.test) ?? null;
  const board = requested?.board ?? BOARDS.find((b) => b === sp.board) ?? null;
  const cls = requested?.class ?? (sp.class && /^\d+$/.test(sp.class) ? Number(sp.class) : null);
  const inFilter = tests.filter((t) => (!board || t.board === board) && (!cls || t.class === cls));

  // Latest test with marks per class: the toppers strip, and the default pick.
  const marks = await marksOf(tests.slice(0, 200).map((t) => t.id));
  const withMarks = new Set(marks.filter((m) => !m.absent && m.score !== null).map((m) => m.test_id));
  const latestPerClass = new Map<string, Test>();
  for (const t of tests) {
    const k = `${t.board}-${t.class}`;
    if (withMarks.has(t.id) && !latestPerClass.has(k)) latestPerClass.set(k, t);
  }
  const test = requested ?? inFilter.find((t) => withMarks.has(t.id)) ?? inFilter[0] ?? null;

  const [ranking, toppers] = await Promise.all([
    test ? loadRanking(test, viewer) : Promise.resolve(null),
    Promise.all(
      [...latestPerClass.values()]
        .sort((a, b) => a.board.localeCompare(b.board) || a.class - b.class)
        .map(async (t) => ({ test: t, ranking: await loadRanking(t, viewer) })),
    ),
  ]);

  const classes = [...new Set(tests.filter((t) => !board || t.board === board).map((t) => t.class))].sort((a, b) => a - b);
  const href = (patch: SP) => {
    const merged: SP = { board: board ?? undefined, class: cls ? String(cls) : undefined, ...patch };
    const q = new URLSearchParams(Object.entries(merged).filter(([, v]) => v) as [string, string][]).toString();
    return `/ranks${q ? `?${q}` : ""}`;
  };

  return (
    <>
      <PageHeader
        title="Ranks"
        subtitle={ranking?.limited ? "Students of your batches (ranks are class ranks)" : "Top 5 in every class"}
        right={
          test ? (
            <a href={`/api/ranks/pdf?test=${test.id}`} className="btn btn-primary py-1.5 text-[13px]">
              <Download size={15} /> PDF
            </a>
          ) : null
        }
      />
      <Page wide>
        {toppers.some((t) => t.ranking.rows.length) && (
          <section>
            <h2 className="mb-2 text-[15px] font-bold text-navy">Class toppers at a glance</h2>
            <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1 lg:mx-0 lg:px-0">
              {toppers
                .filter((t) => t.ranking.rows.length)
                .map(({ test: t, ranking: r }) => {
                  const top = r.rows[0];
                  return (
                    <Link key={t.id} href={href({ board: t.board, class: String(t.class), test: t.id })} className="w-52 shrink-0">
                      <Card className="h-full p-3.5 hover:ring-1 hover:ring-primary">
                        <p className="text-[11.5px] font-bold text-muted">
                          {boardName(t.board)} · Class {t.class}
                        </p>
                        <p className="mt-1 flex items-center gap-1.5 truncate font-extrabold text-navy">
                          <Trophy size={15} className="shrink-0 text-warn" /> {top.student.name}
                        </p>
                        <p className="text-xs text-muted">
                          {top.pct !== null ? `${top.pct}%` : top.score} · {t.name}
                        </p>
                      </Card>
                    </Link>
                  );
                })}
            </div>
          </section>
        )}

        <div className="mt-4 space-y-2">
          <FilterChips
            items={[
              { href: "/ranks", label: "All boards", active: !board },
              ...BOARDS.map((b) => ({ href: `/ranks?board=${b}`, label: boardName(b), active: board === b })),
            ]}
          />
          {classes.length > 0 && (
            <FilterChips
              items={[
                { href: href({ class: undefined, test: undefined }), label: "All classes", active: !cls },
                ...classes.map((c) => ({ href: href({ class: String(c), test: undefined }), label: `Class ${c}`, active: cls === c })),
              ]}
            />
          )}
          {inFilter.length > 0 && (
            <form className="flex items-center gap-2">
              {board && <input type="hidden" name="board" value={board} />}
              {cls && <input type="hidden" name="class" value={cls} />}
              <select name="test" defaultValue={test?.id} className="field max-w-xl py-2" aria-label="Test">
                {inFilter.map((t) => (
                  <option key={t.id} value={t.id}>
                    {dateLabel(t.date)} · {boardName(t.board)} {t.class} · {t.name} ({t.tag}){withMarks.has(t.id) ? "" : " · no marks yet"}
                  </option>
                ))}
              </select>
              <button className="btn btn-soft">Show</button>
            </form>
          )}
        </div>

        {!test || !ranking ? (
          <div className="mt-4">
            <Empty icon={Trophy}>No tests yet. Ranks appear once marks are entered for a test.</Empty>
          </div>
        ) : (
          <RankingView ranking={ranking} />
        )}
      </Page>
    </>
  );
}

const MEDAL = ["text-[#c99a06]", "text-[#8a94a6]", "text-[#b0703a]"];

function RankingView({ ranking }: { ranking: Ranking }) {
  const { test, rows, summary } = ranking;
  // Top 5 by class rank (ties included). A login limited to its own batches sees its first five.
  const top = ranking.limited ? rows.slice(0, 5) : rows.filter((r) => r.rank <= 5);
  return (
    <div className="mt-2 grid gap-x-6 xl:grid-cols-[1fr_360px]">
      <Section
        title={
          <span>
            Top 5 · {boardName(test.board)} {test.class} · {test.name}
          </span>
        }
        action={<Chip tone={test.tag === "School" ? "violet" : "primary"}>{test.tag}</Chip>}
      >
        <p className="-mt-1 mb-2 text-xs text-muted">
          {dateLabel(test.date)}
          {test.subject ? ` · ${test.subject}` : ""}
          {test.max_marks ? ` · Max ${Number(test.max_marks)}` : ""}
        </p>
        {top.length === 0 ? (
          <Empty>No marks entered for this test yet.</Empty>
        ) : (
          <Card className="divide-y divide-line">
            {top.map((r) => (
              <div key={r.student.id} className="flex items-center gap-3 px-4 py-3">
                <div className="grid w-9 shrink-0 place-items-center">
                  {r.rank <= 3 ? <Medal size={24} className={MEDAL[r.rank - 1]} /> : <span className="text-lg font-extrabold text-muted">{r.rank}</span>}
                </div>
                <div className="min-w-0 flex-1">
                  <Link href={`/students/${r.student.id}`} className="block truncate font-bold text-navy hover:underline">
                    {r.student.name}
                  </Link>
                  <p className="truncate text-xs text-muted">
                    Rank {r.rank} · {r.student.code}
                    {r.batch ? ` · ${r.batch}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-extrabold text-navy">
                    {r.score}
                    {test.max_marks ? <span className="text-xs font-semibold text-muted"> / {Number(test.max_marks)}</span> : null}
                  </p>
                  {r.pct !== null && <p className="text-xs font-bold text-primary">{r.pct}%</p>}
                </div>
              </div>
            ))}
          </Card>
        )}
        {rows.length > top.length && <p className="mt-2 text-xs text-muted">Full ranking of {rows.length} students in the PDF.</p>}
      </Section>

      <Section title="Class summary">
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Appeared" value={summary.appeared} hint={summary.absent ? `${summary.absent} absent` : undefined} />
          <Stat label="Class average" value={summary.average !== null ? `${summary.average}%` : "–"} tone="primary" />
        </div>
        <Card className="mt-3 space-y-2.5 p-4">
          <p className="text-xs font-bold text-muted">Score bands</p>
          {BANDS.map((b) => (
            <div key={b} className="flex items-center gap-3 text-sm">
              <span className="w-16 shrink-0 font-semibold">{b}</span>
              <Meter value={summary.bands[b]} max={summary.appeared || 1} tone={b === "90+" ? "ok" : b === "Below 60" ? "danger" : b === "60–74" ? "warn" : "primary"} />
              <span className="w-8 shrink-0 text-right font-bold">{summary.bands[b]}</span>
            </div>
          ))}
          {summary.highest !== null && <p className="pt-1 text-xs text-muted">Highest: {summary.highest}%</p>}
        </Card>
      </Section>
    </div>
  );
}
