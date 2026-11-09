import Link from "next/link";
import { AlertTriangle, CalendarDays, CheckCircle2, ClipboardList, Megaphone, Pencil, Plus, Trash2 } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { batchesFor, batchLabel, batchMap, batchShort } from "@/lib/batches";
import { BOARDS, boardName } from "@/lib/ids";
import { WEEKDAYS, addDays, clockLabel, dayLabel, todayIst } from "@/lib/format";
import { clashKey, facultyNames, findClashes, testsForBatches, timeInput, timetableOf } from "@/lib/academics";
import type { Tag, Test, TimetableEntry } from "@/lib/types";
import { Banner, Card, Chip, Empty, FilterChips, Page, PageHeader, Section } from "@/components/ui";
import { deleteEntry, saveEntry } from "./actions";
import { getT } from "@/lib/i18n/server";
import type { DictKey, TFn } from "@/lib/i18n";

export const metadata = { title: "Timetable & tests" };

type SP = { board?: string; class?: string; batch?: string; tag?: string; saved?: string; test?: string; posted?: string; error?: string };

const ERRORS: Record<string, DictKey> = {
  access: "academics.tt.err.access",
  entry: "academics.tt.err.entry",
  time: "academics.tt.err.time",
  post: "academics.tt.err.post",
  empty: "academics.tt.err.empty",
  fees: "academics.tt.err.fees",
};

const DAY_KEYS: DictKey[] = ["academics.day.1", "academics.day.2", "academics.day.3", "academics.day.4", "academics.day.5", "academics.day.6", "academics.day.7"];

export default async function TimetablePage({ searchParams }: { searchParams: Promise<SP> }) {
  const viewer = await requireStaff();
  const sp = await searchParams;
  const { t } = await getT();
  const canEdit = can(viewer, "academics.edit");
  const canPost = can(viewer, "groups.post_batch");
  const canMarks = can(viewer, "marks.enter") || can(viewer, "students.view");
  const today = todayIst();

  const visible = await batchesFor(viewer);
  const board = BOARDS.find((b) => b === sp.board) ?? null;
  const cls = sp.class && /^\d+$/.test(sp.class) ? Number(sp.class) : null;
  const tag = sp.tag === "School" || sp.tag === "Coaching" ? (sp.tag as Tag) : null;
  const filtered = visible.filter((b) => (!board || b.board === board) && (!cls || b.class === cls));
  const batch = filtered.find((b) => b.id === sp.batch) ?? filtered[0] ?? null;

  const [entries, upcomingAll, recentAll, faculty] = await Promise.all([
    timetableOf(batch ? [batch.id] : []),
    testsForBatches(filtered, today),
    testsForBatches(filtered, addDays(today, -21)),
    facultyNames(),
  ]);
  const clashes = findClashes(upcomingAll);
  const upcoming = upcomingAll.filter((t) => !tag || t.tag === tag);
  const recent = recentAll.filter((t) => t.date < today && (!tag || t.tag === tag)).reverse();
  const shownEntries = entries.filter((e) => !tag || e.tag === tag);
  const bmap = batchMap(visible);

  const href = (patch: Partial<SP>) => {
    const next: Record<string, string> = {};
    const merged = { board: sp.board, class: sp.class, batch: sp.batch, tag: sp.tag, ...patch };
    for (const [k, v] of Object.entries(merged)) if (v) next[k] = String(v);
    const q = new URLSearchParams(next).toString();
    return `/timetable${q ? `?${q}` : ""}`;
  };
  const classes = [...new Set(visible.filter((b) => !board || b.board === board).map((b) => b.class))].sort((a, b) => a - b);
  const savedTest = sp.saved === "test" && sp.test ? upcomingAll.find((t) => t.id === sp.test) ?? recentAll.find((t) => t.id === sp.test) : null;
  const clashCount = [...clashes].length;

  return (
    <>
      <PageHeader
        title={t("academics.tt.title")}
        subtitle={viewer.user.role === "faculty" ? t("academics.tt.subFaculty") : t("academics.tt.sub")}
        right={
          canEdit ? (
            <Link href={`/timetable/test${board && cls ? `?for=class:${board}:${cls}` : ""}`} className="btn btn-primary py-1.5 text-[13px]">
              <Plus size={15} /> {t("academics.tt.testBtn")}
            </Link>
          ) : null
        }
      />
      <Page wide>
        <div className="space-y-2">
          {sp.error && ERRORS[sp.error] && <Banner tone="danger" icon={AlertTriangle}>{t(ERRORS[sp.error])}</Banner>}
          {sp.posted && (
            <Banner tone="ok" icon={CheckCircle2}>
              {t("academics.tt.posted", { n: sp.posted })}
            </Banner>
          )}
          {sp.saved === "deleted" && <Banner tone="ok" icon={CheckCircle2}>{t("academics.tt.deleted")}</Banner>}
          {sp.saved === "timetable" && batch && (
            <Banner tone="ok" icon={CheckCircle2}>
              {t("academics.tt.saved")}{" "}
              {canPost && (
                <Link href={`/timetable/post?kind=timetable&batch=${batch.id}`} className="font-bold underline">
                  {t("academics.tt.postChange")}
                </Link>
              )}
            </Banner>
          )}
          {savedTest && (
            <Banner tone="ok" icon={CheckCircle2}>
              {t("academics.tt.savedTest", { name: savedTest.name })}{" "}
              {canPost && (
                <Link href={`/timetable/post?kind=test&id=${savedTest.id}`} className="font-bold underline">
                  {t("academics.tt.postIt")}
                </Link>
              )}
            </Banner>
          )}
        </div>

        <div className="mt-3 space-y-2">
          <FilterChips
            items={[
              { href: href({ board: undefined, class: undefined, batch: undefined }), label: t("academics.allBoards"), active: !board },
              ...BOARDS.map((b) => ({ href: href({ board: b, class: undefined, batch: undefined }), label: boardName(b), active: board === b })),
            ]}
          />
          {classes.length > 1 && (
            <FilterChips
              items={[
                { href: href({ class: undefined, batch: undefined }), label: t("academics.allClasses"), active: !cls },
                ...classes.map((c) => ({ href: href({ class: String(c), batch: undefined }), label: t("academics.class", { n: c }), active: cls === c })),
              ]}
            />
          )}
          <FilterChips
            items={[
              { href: href({ tag: undefined }), label: t("academics.tt.schoolCoaching"), active: !tag },
              { href: href({ tag: "School" }), label: t("academics.tag.School"), active: tag === "School" },
              { href: href({ tag: "Coaching" }), label: t("academics.tag.Coaching"), active: tag === "Coaching" },
            ]}
          />
        </div>

        {visible.length === 0 ? (
          <div className="mt-4">
            <Empty icon={CalendarDays}>{viewer.user.role === "faculty" ? t("academics.tt.noBatchesFaculty") : t("academics.att.noBatches")}</Empty>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-x-6 2xl:grid-cols-[1fr_400px]">
            <div>
              <Section
                title={batch ? t("academics.tt.weeklyFor", { batch: batchLabel(batch) }) : t("academics.tt.weekly")}
                action={
                  filtered.length > 1 ? (
                    <form className="flex items-center gap-2">
                      {board && <input type="hidden" name="board" value={board} />}
                      {cls && <input type="hidden" name="class" value={cls} />}
                      {tag && <input type="hidden" name="tag" value={tag} />}
                      <select name="batch" defaultValue={batch?.id} className="field py-1.5 text-[13px]" aria-label={t("academics.batch")}>
                        {filtered.map((b) => (
                          <option key={b.id} value={b.id}>
                            {batchLabel(b)}
                          </option>
                        ))}
                      </select>
                      <button className="btn btn-soft py-1.5 text-[13px]">{t("academics.show")}</button>
                    </form>
                  ) : null
                }
              >
                {!batch ? (
                  <Empty>{t("academics.tt.noBatchMatch")}</Empty>
                ) : (
                  <>
                    <div className="grid grid-cols-1 gap-2 lg:grid-cols-7">
                      {WEEKDAYS.map((day, i) => {
                        const list = shownEntries.filter((e) => e.weekday === i + 1);
                        return (
                          <Card key={day} className={`p-3 ${list.length === 0 ? "hidden lg:block" : ""}`}>
                            <p className="mb-2 text-xs font-extrabold tracking-wide text-navy uppercase">{t(DAY_KEYS[i])}</p>
                            {list.length === 0 ? (
                              <p className="text-xs text-faint">{t("academics.tt.noClass")}</p>
                            ) : (
                              <ul className="space-y-2">
                                {list.map((e) => (
                                  <EntryItem key={e.id} e={e} faculty={faculty.get(e.faculty_id ?? "")} canEdit={canEdit} facultyList={faculty} t={t} />
                                ))}
                              </ul>
                            )}
                          </Card>
                        );
                      })}
                    </div>
                    {shownEntries.length === 0 && <p className="mt-2 text-sm text-muted">{t("academics.tt.noClasses")}</p>}
                    {canEdit && (
                      <details className="mt-3 rounded-card bg-card p-4 shadow-card">
                        <summary className="flex cursor-pointer items-center gap-2 text-sm font-bold text-primary">
                          <Plus size={16} /> {t("academics.tt.addClassTo", { batch: batchShort(batch) })}
                        </summary>
                        <EntryForm batchId={batch.id} facultyList={faculty} t={t} />
                      </details>
                    )}
                    {canPost && shownEntries.length > 0 && (
                      <div className="mt-2">
                        <Link href={`/timetable/post?kind=timetable&batch=${batch.id}`} className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary">
                          <Megaphone size={15} /> {t("academics.tt.postTimetable")}
                        </Link>
                      </div>
                    )}
                  </>
                )}
              </Section>
            </div>

            <div>
              <Section title={t("academics.tt.upcoming")}>
                {clashCount > 0 && (
                  <div className="mb-2">
                    <Banner tone="warn" icon={AlertTriangle}>
                      {clashCount === 1 ? t("academics.tt.clash1") : t("academics.tt.clashN", { n: clashCount })}
                    </Banner>
                  </div>
                )}
                {upcoming.length === 0 ? (
                  <Empty icon={ClipboardList}>{t("academics.tt.noUpcoming")}</Empty>
                ) : (
                  <Card className="divide-y divide-line">
                    {upcoming.map((x) => (
                      <TestRow key={x.id} test={x} batchName={x.batch_id ? (bmap.get(x.batch_id) ? batchShort(bmap.get(x.batch_id)!) : t("academics.batch")) : t("academics.wholeClass")} clash={clashes.has(clashKey(x))} canEdit={canEdit} canPost={canPost} canMarks={false} t={t} />
                    ))}
                  </Card>
                )}
              </Section>
              {canMarks && (
                <Section title={t("academics.tt.recentMarks")}>
                  {recent.length === 0 ? (
                    <Empty>{t("academics.tt.noRecent")}</Empty>
                  ) : (
                    <Card className="divide-y divide-line">
                      {recent.map((x) => (
                        <TestRow key={x.id} test={x} batchName={x.batch_id ? (bmap.get(x.batch_id) ? batchShort(bmap.get(x.batch_id)!) : t("academics.batch")) : t("academics.wholeClass")} clash={false} canEdit={canEdit} canPost={false} canMarks t={t} />
                      ))}
                    </Card>
                  )}
                </Section>
              )}
            </div>
          </div>
        )}
      </Page>
    </>
  );
}

function TagChip({ tag, t }: { tag: Tag; t: TFn }) {
  return <Chip tone={tag === "School" ? "violet" : "primary"}>{t(tag === "School" ? "academics.tag.School" : "academics.tag.Coaching")}</Chip>;
}

function TestRow({
  test,
  batchName,
  clash,
  canEdit,
  canPost,
  canMarks,
  t,
}: {
  test: Test;
  batchName: string;
  clash: boolean;
  canEdit: boolean;
  canPost: boolean;
  canMarks: boolean;
  t: TFn;
}) {
  const x = test;
  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-bold text-navy">{x.name}</p>
          <p className="text-xs text-muted">
            {dayLabel(x.date)}
            {x.start_time ? ` · ${clockLabel(x.start_time)}` : ""} · {boardName(x.board)} {x.class} · {batchName}
            {x.subject ? ` · ${x.subject}` : ""}
            {x.max_marks ? ` · ${t("academics.max", { n: Number(x.max_marks) })}` : ""}
          </p>
        </div>
        <TagChip tag={x.tag} t={t} />
      </div>
      {clash && (
        <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-warn">
          <AlertTriangle size={13} /> {t("academics.tt.clashRow")}
        </p>
      )}
      {(canEdit || canPost || canMarks) && (
        <div className="mt-1.5 flex flex-wrap gap-3 text-[13px] font-bold text-primary">
          {canMarks && <Link href={`/tests/${x.id}`}>{t("academics.tt.marks")}</Link>}
          {canEdit && <Link href={`/timetable/test?id=${x.id}`}>{t("core.edit")}</Link>}
          {canPost && <Link href={`/timetable/post?kind=test&id=${x.id}`}>{t("academics.tt.postToGroup")}</Link>}
        </div>
      )}
    </div>
  );
}

function EntryItem({ e, faculty, canEdit, facultyList, t }: { e: TimetableEntry; faculty?: string; canEdit: boolean; facultyList: Map<string, string>; t: TFn }) {
  return (
    <li className="rounded-field bg-field px-2.5 py-2">
      <p className="text-[11.5px] font-bold text-muted">
        {clockLabel(e.start_time)}
        {e.end_time ? `–${clockLabel(e.end_time)}` : ""}
      </p>
      <p className="text-[13.5px] font-bold">{e.subject}</p>
      <div className="mt-0.5 flex flex-wrap items-center gap-1">
        {faculty && <span className="text-[11.5px] text-muted">{faculty}</span>}
        <TagChip tag={e.tag} t={t} />
      </div>
      {canEdit && (
        <details className="mt-1">
          <summary className="flex cursor-pointer items-center gap-1 text-[12px] font-bold text-primary">
            <Pencil size={12} /> {t("core.edit")}
          </summary>
          <EntryForm batchId={e.batch_id} entry={e} facultyList={facultyList} t={t} />
          <form action={deleteEntry} className="mt-2">
            <input type="hidden" name="id" value={e.id} />
            <button className="btn btn-danger w-full py-1.5 text-[12px]">
              <Trash2 size={13} /> {t("academics.tt.remove")}
            </button>
          </form>
        </details>
      )}
    </li>
  );
}

function EntryForm({ batchId, entry, facultyList, t }: { batchId: string; entry?: TimetableEntry; facultyList: Map<string, string>; t: TFn }) {
  return (
    <form action={saveEntry} className="mt-3 grid gap-2 sm:grid-cols-2">
      <input type="hidden" name="batch_id" value={batchId} />
      {entry && <input type="hidden" name="id" value={entry.id} />}
      <div>
        <label className="label">{t("academics.tt.day")}</label>
        <select name="weekday" defaultValue={entry?.weekday ?? 1} className="field">
          {WEEKDAYS.map((d, i) => (
            <option key={d} value={i + 1}>
              {t(DAY_KEYS[i])}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">{t("academics.tt.subject")}</label>
        <input name="subject" required defaultValue={entry?.subject} placeholder="Physics" className="field" />
      </div>
      <div>
        <label className="label">{t("academics.tt.start")}</label>
        <input type="time" name="start_time" required defaultValue={timeInput(entry?.start_time)} className="field" />
      </div>
      <div>
        <label className="label">{t("academics.tt.end")}</label>
        <input type="time" name="end_time" defaultValue={timeInput(entry?.end_time)} className="field" />
      </div>
      <div>
        <label className="label">{t("academics.tt.faculty")}</label>
        <select name="faculty_id" defaultValue={entry?.faculty_id ?? ""} className="field">
          <option value="">—</option>
          {[...facultyList].map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">{t("academics.tt.tag")}</label>
        <select name="tag" defaultValue={entry?.tag ?? "Coaching"} className="field">
          <option value="Coaching">{t("academics.tag.Coaching")}</option>
          <option value="School">{t("academics.tag.School")}</option>
        </select>
      </div>
      <button className="btn btn-primary sm:col-span-2">{entry ? t("academics.tt.saveChanges") : t("academics.tt.addClass")}</button>
    </form>
  );
}
