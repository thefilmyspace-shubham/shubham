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

export const metadata = { title: "Timetable & tests" };

type SP = { board?: string; class?: string; batch?: string; tag?: string; saved?: string; test?: string; posted?: string; error?: string };

const ERRORS: Record<string, string> = {
  access: "Only Admin and Management can change the timetable and tests.",
  entry: "Could not save that class. Check the fields and try again.",
  time: "The end time must be after the start time.",
  post: "Your login cannot post in batch groups.",
  empty: "Write a message and pick at least one batch.",
  fees: "Batch groups are read by every parent in the batch. Fee messages are never posted here.",
};

export default async function TimetablePage({ searchParams }: { searchParams: Promise<SP> }) {
  const viewer = await requireStaff();
  const sp = await searchParams;
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
        title="Timetable & tests"
        subtitle={viewer.user.role === "faculty" ? "Your batches" : "Weekly classes, school exams and coaching tests"}
        right={
          canEdit ? (
            <Link href={`/timetable/test${board && cls ? `?for=class:${board}:${cls}` : ""}`} className="btn btn-primary py-1.5 text-[13px]">
              <Plus size={15} /> Test / exam
            </Link>
          ) : null
        }
      />
      <Page wide>
        <div className="space-y-2">
          {sp.error && ERRORS[sp.error] && <Banner tone="danger" icon={AlertTriangle}>{ERRORS[sp.error]}</Banner>}
          {sp.posted && (
            <Banner tone="ok" icon={CheckCircle2}>
              Posted in {sp.posted} batch {sp.posted === "1" ? "group" : "groups"}. Parents got a notification.
            </Banner>
          )}
          {sp.saved === "deleted" && <Banner tone="ok" icon={CheckCircle2}>Test deleted.</Banner>}
          {sp.saved === "timetable" && batch && (
            <Banner tone="ok" icon={CheckCircle2}>
              Timetable saved.{" "}
              {canPost && (
                <Link href={`/timetable/post?kind=timetable&batch=${batch.id}`} className="font-bold underline">
                  Post the change to the batch group →
                </Link>
              )}
            </Banner>
          )}
          {savedTest && (
            <Banner tone="ok" icon={CheckCircle2}>
              Saved “{savedTest.name}”.{" "}
              {canPost && (
                <Link href={`/timetable/post?kind=test&id=${savedTest.id}`} className="font-bold underline">
                  Post it to the batch group →
                </Link>
              )}
            </Banner>
          )}
        </div>

        <div className="mt-3 space-y-2">
          <FilterChips
            items={[
              { href: href({ board: undefined, class: undefined, batch: undefined }), label: "All boards", active: !board },
              ...BOARDS.map((b) => ({ href: href({ board: b, class: undefined, batch: undefined }), label: boardName(b), active: board === b })),
            ]}
          />
          {classes.length > 1 && (
            <FilterChips
              items={[
                { href: href({ class: undefined, batch: undefined }), label: "All classes", active: !cls },
                ...classes.map((c) => ({ href: href({ class: String(c), batch: undefined }), label: `Class ${c}`, active: cls === c })),
              ]}
            />
          )}
          <FilterChips
            items={[
              { href: href({ tag: undefined }), label: "School + Coaching", active: !tag },
              { href: href({ tag: "School" }), label: "School", active: tag === "School" },
              { href: href({ tag: "Coaching" }), label: "Coaching", active: tag === "Coaching" },
            ]}
          />
        </div>

        {visible.length === 0 ? (
          <div className="mt-4">
            <Empty icon={CalendarDays}>{viewer.user.role === "faculty" ? "No batches are assigned to you yet." : "No batches yet. Admin adds them in Batches & faculty."}</Empty>
          </div>
        ) : (
          <div className="grid gap-x-6 2xl:grid-cols-[1fr_400px]">
            <div>
              <Section
                title={batch ? `Weekly timetable · ${batchLabel(batch)}` : "Weekly timetable"}
                action={
                  filtered.length > 1 ? (
                    <form className="flex items-center gap-2">
                      {board && <input type="hidden" name="board" value={board} />}
                      {cls && <input type="hidden" name="class" value={cls} />}
                      {tag && <input type="hidden" name="tag" value={tag} />}
                      <select name="batch" defaultValue={batch?.id} className="field py-1.5 text-[13px]" aria-label="Batch">
                        {filtered.map((b) => (
                          <option key={b.id} value={b.id}>
                            {batchLabel(b)}
                          </option>
                        ))}
                      </select>
                      <button className="btn btn-soft py-1.5 text-[13px]">Show</button>
                    </form>
                  ) : null
                }
              >
                {!batch ? (
                  <Empty>No batch matches these filters.</Empty>
                ) : (
                  <>
                    <div className="grid gap-2 lg:grid-cols-7">
                      {WEEKDAYS.map((day, i) => {
                        const list = shownEntries.filter((e) => e.weekday === i + 1);
                        return (
                          <Card key={day} className={`p-3 ${list.length === 0 ? "hidden lg:block" : ""}`}>
                            <p className="mb-2 text-xs font-extrabold tracking-wide text-navy uppercase">{day}</p>
                            {list.length === 0 ? (
                              <p className="text-xs text-faint">No class</p>
                            ) : (
                              <ul className="space-y-2">
                                {list.map((e) => (
                                  <EntryItem key={e.id} e={e} faculty={faculty.get(e.faculty_id ?? "")} canEdit={canEdit} facultyList={faculty} />
                                ))}
                              </ul>
                            )}
                          </Card>
                        );
                      })}
                    </div>
                    {shownEntries.length === 0 && <p className="mt-2 text-sm text-muted">No classes in the timetable for this batch yet.</p>}
                    {canEdit && (
                      <details className="mt-3 rounded-card bg-card p-4 shadow-card">
                        <summary className="flex cursor-pointer items-center gap-2 text-sm font-bold text-primary">
                          <Plus size={16} /> Add a class to {batchShort(batch)}
                        </summary>
                        <EntryForm batchId={batch.id} facultyList={faculty} />
                      </details>
                    )}
                    {canPost && shownEntries.length > 0 && (
                      <div className="mt-2">
                        <Link href={`/timetable/post?kind=timetable&batch=${batch.id}`} className="inline-flex items-center gap-1.5 text-[13px] font-bold text-primary">
                          <Megaphone size={15} /> Post this timetable to the batch group
                        </Link>
                      </div>
                    )}
                  </>
                )}
              </Section>
            </div>

            <div>
              <Section title="Upcoming exams and tests">
                {clashCount > 0 && (
                  <div className="mb-2">
                    <Banner tone="warn" icon={AlertTriangle}>
                      {clashCount === 1 ? "One day has" : `${clashCount} days have`} a school exam and a coaching test for the same class. Consider moving the coaching test.
                    </Banner>
                  </div>
                )}
                {upcoming.length === 0 ? (
                  <Empty icon={ClipboardList}>No upcoming tests or exams.</Empty>
                ) : (
                  <Card className="divide-y divide-line">
                    {upcoming.map((t) => (
                      <TestRow key={t.id} t={t} batchName={t.batch_id ? (bmap.get(t.batch_id) ? batchShort(bmap.get(t.batch_id)!) : "Batch") : "Whole class"} clash={clashes.has(clashKey(t))} canEdit={canEdit} canPost={canPost} canMarks={false} />
                    ))}
                  </Card>
                )}
              </Section>
              {canMarks && (
                <Section title="Recent tests (marks)">
                  {recent.length === 0 ? (
                    <Empty>No tests in the last three weeks.</Empty>
                  ) : (
                    <Card className="divide-y divide-line">
                      {recent.map((t) => (
                        <TestRow key={t.id} t={t} batchName={t.batch_id ? (bmap.get(t.batch_id) ? batchShort(bmap.get(t.batch_id)!) : "Batch") : "Whole class"} clash={false} canEdit={canEdit} canPost={false} canMarks />
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

function TagChip({ tag }: { tag: Tag }) {
  return <Chip tone={tag === "School" ? "violet" : "primary"}>{tag}</Chip>;
}

function TestRow({ t, batchName, clash, canEdit, canPost, canMarks }: { t: Test; batchName: string; clash: boolean; canEdit: boolean; canPost: boolean; canMarks: boolean }) {
  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-bold text-navy">{t.name}</p>
          <p className="text-xs text-muted">
            {dayLabel(t.date)}
            {t.start_time ? ` · ${clockLabel(t.start_time)}` : ""} · {boardName(t.board)} {t.class} · {batchName}
            {t.subject ? ` · ${t.subject}` : ""}
            {t.max_marks ? ` · Max ${Number(t.max_marks)}` : ""}
          </p>
        </div>
        <TagChip tag={t.tag} />
      </div>
      {clash && (
        <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-warn">
          <AlertTriangle size={13} /> Clash: school exam and coaching test on the same day
        </p>
      )}
      {(canEdit || canPost || canMarks) && (
        <div className="mt-1.5 flex flex-wrap gap-3 text-[13px] font-bold text-primary">
          {canMarks && <Link href={`/tests/${t.id}`}>Marks</Link>}
          {canEdit && <Link href={`/timetable/test?id=${t.id}`}>Edit</Link>}
          {canPost && <Link href={`/timetable/post?kind=test&id=${t.id}`}>Post to group</Link>}
        </div>
      )}
    </div>
  );
}

function EntryItem({ e, faculty, canEdit, facultyList }: { e: TimetableEntry; faculty?: string; canEdit: boolean; facultyList: Map<string, string> }) {
  return (
    <li className="rounded-field bg-field px-2.5 py-2">
      <p className="text-[11.5px] font-bold text-muted">
        {clockLabel(e.start_time)}
        {e.end_time ? `–${clockLabel(e.end_time)}` : ""}
      </p>
      <p className="text-[13.5px] font-bold">{e.subject}</p>
      <div className="mt-0.5 flex flex-wrap items-center gap-1">
        {faculty && <span className="text-[11.5px] text-muted">{faculty}</span>}
        <TagChip tag={e.tag} />
      </div>
      {canEdit && (
        <details className="mt-1">
          <summary className="flex cursor-pointer items-center gap-1 text-[12px] font-bold text-primary">
            <Pencil size={12} /> Edit
          </summary>
          <EntryForm batchId={e.batch_id} entry={e} facultyList={facultyList} />
          <form action={deleteEntry} className="mt-2">
            <input type="hidden" name="id" value={e.id} />
            <button className="btn btn-danger w-full py-1.5 text-[12px]">
              <Trash2 size={13} /> Remove
            </button>
          </form>
        </details>
      )}
    </li>
  );
}

function EntryForm({ batchId, entry, facultyList }: { batchId: string; entry?: TimetableEntry; facultyList: Map<string, string> }) {
  return (
    <form action={saveEntry} className="mt-3 grid gap-2 sm:grid-cols-2">
      <input type="hidden" name="batch_id" value={batchId} />
      {entry && <input type="hidden" name="id" value={entry.id} />}
      <div>
        <label className="label">Day</label>
        <select name="weekday" defaultValue={entry?.weekday ?? 1} className="field">
          {WEEKDAYS.map((d, i) => (
            <option key={d} value={i + 1}>
              {d}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Subject</label>
        <input name="subject" required defaultValue={entry?.subject} placeholder="Physics" className="field" />
      </div>
      <div>
        <label className="label">Start</label>
        <input type="time" name="start_time" required defaultValue={timeInput(entry?.start_time)} className="field" />
      </div>
      <div>
        <label className="label">End</label>
        <input type="time" name="end_time" defaultValue={timeInput(entry?.end_time)} className="field" />
      </div>
      <div>
        <label className="label">Faculty</label>
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
        <label className="label">Tag</label>
        <select name="tag" defaultValue={entry?.tag ?? "Coaching"} className="field">
          <option>Coaching</option>
          <option>School</option>
        </select>
      </div>
      <button className="btn btn-primary sm:col-span-2">{entry ? "Save changes" : "Add class"}</button>
    </form>
  );
}
