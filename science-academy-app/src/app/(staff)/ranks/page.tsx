import Link from "next/link";
import { Download, Medal, Trophy } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { BOARDS, boardName } from "@/lib/ids";
import { dateLabel, todayIst } from "@/lib/format";
import { BANDS, loadRanking, marksOf, rankableTests, type Ranking } from "@/lib/academics";
import type { Test } from "@/lib/types";
import { Meter } from "@/components/BarChart";
import { Card, Chip, Empty, FilterChips, Page, PageHeader, Section, Stat } from "@/components/ui";
import { getT } from "@/lib/i18n/server";
import type { TFn } from "@/lib/i18n";

export const metadata = { title: "Ranks" };

type SP = { board?: string; class?: string; test?: string };

export default async function RanksPage({ searchParams }: { searchParams: Promise<SP> }) {
  const viewer = await requirePermission("ranks.view");
  const sp = await searchParams;
  const { t } = await getT();
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
        title={t("academics.ranks.title")}
        subtitle={ranking?.limited ? t("academics.ranks.subLimited") : t("academics.ranks.subTop5")}
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
            <h2 className="mb-2 text-[15px] font-bold text-navy">{t("academics.ranks.toppers")}</h2>
            <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1 lg:mx-0 lg:px-0">
              {toppers
                .filter((t) => t.ranking.rows.length)
                .map(({ test: tt, ranking: r }) => {
                  const top = r.rows[0];
                  return (
                    <Link key={tt.id} href={href({ board: tt.board, class: String(tt.class), test: tt.id })} className="w-52 shrink-0">
                      <Card className="h-full p-3.5 hover:ring-1 hover:ring-primary">
                        <p className="text-[11.5px] font-bold text-muted">
                          {t("academics.ranks.boardClass", { board: boardName(tt.board), c: tt.class })}
                        </p>
                        <p className="mt-1 flex items-center gap-1.5 truncate font-extrabold text-navy">
                          <Trophy size={15} className="shrink-0 text-warn" /> {top.student.name}
                        </p>
                        <p className="text-xs text-muted">
                          {top.pct !== null ? `${top.pct}%` : top.score} · {tt.name}
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
              { href: "/ranks", label: t("academics.allBoards"), active: !board },
              ...BOARDS.map((b) => ({ href: `/ranks?board=${b}`, label: boardName(b), active: board === b })),
            ]}
          />
          {classes.length > 0 && (
            <FilterChips
              items={[
                { href: href({ class: undefined, test: undefined }), label: t("academics.allClasses"), active: !cls },
                ...classes.map((c) => ({ href: href({ class: String(c), test: undefined }), label: t("academics.class", { n: c }), active: cls === c })),
              ]}
            />
          )}
          {inFilter.length > 0 && (
            <form className="flex items-center gap-2">
              {board && <input type="hidden" name="board" value={board} />}
              {cls && <input type="hidden" name="class" value={cls} />}
              <select name="test" defaultValue={test?.id} className="field max-w-xl py-2" aria-label={t("academics.testLabel")}>
                {inFilter.map((x) => (
                  <option key={x.id} value={x.id}>
                    {dateLabel(x.date)} · {boardName(x.board)} {x.class} · {x.name} ({t(x.tag === "School" ? "academics.tag.School" : "academics.tag.Coaching")})
                    {withMarks.has(x.id) ? "" : t("academics.ranks.noMarksYet")}
                  </option>
                ))}
              </select>
              <button className="btn btn-soft">{t("academics.show")}</button>
            </form>
          )}
        </div>

        {!test || !ranking ? (
          <div className="mt-4">
            <Empty icon={Trophy}>{t("academics.ranks.noTests")}</Empty>
          </div>
        ) : (
          <RankingView ranking={ranking} t={t} />
        )}
      </Page>
    </>
  );
}

const MEDAL = ["text-[#c99a06]", "text-[#8a94a6]", "text-[#b0703a]"];

function RankingView({ ranking, t }: { ranking: Ranking; t: TFn }) {
  const { test, rows, summary } = ranking;
  // Top 5 by class rank (ties included). A login limited to its own batches sees its first five.
  const top = ranking.limited ? rows.slice(0, 5) : rows.filter((r) => r.rank <= 5);
  return (
    <div className="mt-2 grid gap-x-6 xl:grid-cols-[1fr_360px]">
      <Section
        title={
          <span>{t("academics.ranks.top5Title", { board: boardName(test.board), c: test.class, test: test.name })}</span>
        }
        action={<Chip tone={test.tag === "School" ? "violet" : "primary"}>{t(test.tag === "School" ? "academics.tag.School" : "academics.tag.Coaching")}</Chip>}
      >
        <p className="-mt-1 mb-2 text-xs text-muted">
          {dateLabel(test.date)}
          {test.subject ? ` · ${test.subject}` : ""}
          {test.max_marks ? ` · ${t("academics.max", { n: Number(test.max_marks) })}` : ""}
        </p>
        {top.length === 0 ? (
          <Empty>{t("academics.ranks.noMarksEntered")}</Empty>
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
                    {t("academics.ranks.rankLine", { r: r.rank, code: r.student.code ?? "" })}
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
        {rows.length > top.length && <p className="mt-2 text-xs text-muted">{t("academics.ranks.full", { n: rows.length })}</p>}
      </Section>

      <Section title={t("academics.ranks.summary")}>
        <div className="grid grid-cols-2 gap-3">
          <Stat label={t("academics.ranks.appeared")} value={summary.appeared} hint={summary.absent ? t("academics.ranks.absentN", { n: summary.absent }) : undefined} />
          <Stat label={t("academics.ranks.classAverage")} value={summary.average !== null ? `${summary.average}%` : "–"} tone="primary" />
        </div>
        <Card className="mt-3 space-y-2.5 p-4">
          <p className="text-xs font-bold text-muted">{t("academics.ranks.bands")}</p>
          {BANDS.map((b) => (
            <div key={b} className="flex items-center gap-3 text-sm">
              <span className="w-16 shrink-0 font-semibold">{b === "Below 60" ? t("academics.ranks.below60") : b}</span>
              <Meter value={summary.bands[b]} max={summary.appeared || 1} tone={b === "90+" ? "ok" : b === "Below 60" ? "danger" : b === "60–74" ? "warn" : "primary"} />
              <span className="w-8 shrink-0 text-right font-bold">{summary.bands[b]}</span>
            </div>
          ))}
          {summary.highest !== null && <p className="pt-1 text-xs text-muted">{t("academics.ranks.highest", { n: summary.highest })}</p>}
        </Card>
      </Section>
    </div>
  );
}
