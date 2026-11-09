import { SubmitButton } from "@/components/SubmitButton";
import { ArrowRight, CheckCircle2, GraduationCap, TriangleAlert } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { allBatches, batchShort } from "@/lib/batches";
import { boardName, formatStudentId, sessionLabel, type Board } from "@/lib/ids";
import type { Student } from "@/lib/types";
import { Banner, Card, Empty, Page, PageHeader, Section } from "@/components/ui";
import { promoteClass } from "./actions";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Year-end promotion" };

type Search = { board?: string; class?: string; batch?: string; session?: string; done?: string; passed?: string; error?: string };

export default async function PromotionPage({ searchParams }: { searchParams: Promise<Search> }) {
  await requirePermission("admin.promotion");
  const { t } = await getT();
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
      <PageHeader title={t("students.promo.title")} subtitle={t("students.promo.subtitle")} />
      <Page>
        {sp.done !== undefined && (
          <Banner tone="ok" icon={CheckCircle2}>
            {t("students.promo.done", { n: sp.done, passed: Number(sp.passed) ? t("students.promo.passedCount", { n: sp.passed ?? "" }) : "" })}
          </Banner>
        )}
        {sp.error === "confirm" && <Banner tone="danger">{t("students.promo.errConfirm")}</Banner>}
        {sp.error === "batch" && <Banner tone="danger">{t("students.promo.errBatch")}</Banner>}

        <Section title={t("students.promo.step1")}>
          <Card className="p-4">
            <form className="grid grid-cols-1 gap-3 sm:grid-cols-4" method="get">
              <div>
                <label className="label" htmlFor="board">
                  {t("students.board")}
                </label>
                <select id="board" name="board" className="field" defaultValue={board ?? ""}>
                  <option value="">{t("students.choose")}</option>
                  <option value="CB">CBSE</option>
                  <option value="MP">MP Board</option>
                </select>
              </div>
              <div>
                <label className="label" htmlFor="class">
                  {t("students.class")}
                </label>
                <select id="class" name="class" className="field" defaultValue={cls ?? ""}>
                  <option value="">{t("students.choose")}</option>
                  {[6, 7, 8, 9, 10, 11, 12].map((c) => (
                    <option key={c} value={c}>
                      {t("students.classN", { n: c })}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="batch">
                  {t("students.promo.batchOptional")}
                </label>
                <select id="batch" name="batch" className="field" defaultValue={batch ?? ""}>
                  <option value="">{t("students.promo.wholeClass")}</option>
                  {classBatches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {batchShort(b)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button className="btn btn-soft w-full">{t("students.promo.show")}</button>
              </div>
            </form>
            {sessions.length > 1 && (
              <p className="mt-3 text-xs text-muted">
                {t("students.promo.manySessions", { session: fromSession !== null ? sessionLabel(fromSession) : "" })}{" "}
                {sessions
                  .filter((s) => s !== fromSession)
                  .map((s) => (
                    <a key={s} className="font-bold text-primary" href={`?board=${board}&class=${cls}${batch ? `&batch=${batch}` : ""}&session=${s}`}>
                      {sessionLabel(s)}{" "}
                    </a>
                  ))}
              </p>
            )}
            <p className="mt-3 text-xs text-muted">{t("students.promo.tip")}</p>
          </Card>
        </Section>

        {board && cls && (
          <Section
            title={t("students.promo.step2", {
              board: boardName(board),
              cls,
              to: cls < 12 ? t("students.classN", { n: cls + 1 }) : t("students.passedOut"),
            })}
          >
            {!students.length ? (
              <Empty icon={GraduationCap}>{t("students.promo.none")}</Empty>
            ) : (
              <>
                <Card className="max-h-[420px] divide-y divide-line overflow-y-auto">
                  {students.map((s) => (
                    <div key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm">
                      <span className="min-w-0 flex-1 font-semibold">{s.name}</span>
                      <span className="text-xs text-muted">{s.batch_id ? batchName.get(s.batch_id) : t("students.noBatch")}</span>
                      <span className="font-mono text-[12.5px]">{s.code}</span>
                      <ArrowRight size={14} className="text-faint" />
                      <span className="font-mono text-[12.5px] font-bold text-green">
                        {cls < 12 ? formatStudentId(s.board, cls + 1, s.roll_number!, s.session_year + 1)   : t("students.passedOut")}
                      </span>
                    </div>
                  ))}
                </Card>

                <Section title={t("students.promo.step3")}>
                  <Card className="p-4">
                    <form action={promoteClass} className="space-y-3">
                      <input type="hidden" name="board" value={board} />
                      <input type="hidden" name="class" value={cls} />
                      <input type="hidden" name="from_session" value={fromSession ?? ""} />
                      {batch && <input type="hidden" name="batch" value={batch} />}
                      {cls < 12 && (
                        <div>
                          <label className="label" htmlFor="target_batch">
                            {t("students.promo.newBatch", { n: cls + 1 })}
                          </label>
                          <select id="target_batch" name="target_batch" className="field" defaultValue="">
                            <option value="">{t("students.promo.noBatchYet")}</option>
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
                          ? t("students.promo.moveWarn", { n: students.length, to: cls + 1, session: sessionLabel((fromSession ?? 0) + 1) })
                          : t("students.promo.passWarn", { n: students.length })}
                      </Banner>
                      <label className="flex items-center gap-2 text-sm font-semibold">
                        <input type="checkbox" name="confirm" className="h-4 w-4 accent-[var(--color-primary)]" /> {t("students.promo.checked")}
                      </label>
                      <SubmitButton className="btn btn-primary w-full sm:w-auto">
                        <GraduationCap size={16} /> {t("students.promo.button", { n: students.length })}
                      </SubmitButton>
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
