import Link from "next/link";
import { notFound } from "next/navigation";
import { AlertTriangle, CheckCircle2, ChevronRight, ClipboardCheck, Clock } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { batchesFor, batchShort } from "@/lib/batches";
import { boardName } from "@/lib/ids";
import { dayLabel, todayIst } from "@/lib/format";
import { activeStudentsOfBatches } from "@/lib/academics";
import { attendanceOn, countStatuses } from "@/lib/attendance";
import { Card, Chip, Empty, Page, PageHeader, Section, SectionLink } from "@/components/ui";

export const metadata = { title: "Attendance" };

export default async function AttendancePage() {
  const viewer = await requireStaff();
  if (!can(viewer, "attendance.mark") && !can(viewer, "students.view")) notFound();
  const canMark = can(viewer, "attendance.mark");
  const today = todayIst();
  const batches = await batchesFor(viewer);
  const students = await activeStudentsOfBatches(batches.map((b) => b.id));
  const rows = await attendanceOn(
    students.map((s) => s.id),
    today,
  );
  const statusOf = new Map(rows.map((r) => [r.student_id, r.status]));

  // Board, then class, then batch.
  const groups = new Map<string, typeof batches>();
  for (const b of batches) {
    const k = `${boardName(b.board)} · Class ${b.class}`;
    groups.set(k, [...(groups.get(k) ?? []), b]);
  }
  const notMarked = batches.filter((b) => {
    const list = students.filter((s) => s.batch_id === b.id);
    return list.length > 0 && list.every((s) => !statusOf.has(s.id));
  }).length;

  return (
    <>
      <PageHeader
        title="Attendance"
        subtitle={`Today · ${dayLabel(today)}${canMark ? "" : " · view only"}`}
        right={
          <Link href="/attendance/low" className="btn btn-ghost py-1.5 text-[13px]">
            <AlertTriangle size={15} /> Low attendance
          </Link>
        }
      />
      <Page>
        {batches.length === 0 ? (
          <Empty icon={ClipboardCheck}>
            {viewer.user.role === "faculty" ? "No batches are assigned to you yet. Admin assigns batches in Batches & faculty." : "No batches yet. Admin adds them in Batches & faculty."}
          </Empty>
        ) : (
          <>
            {notMarked > 0 && (
              <p className="mb-1 text-sm font-semibold text-warn">
                {notMarked} {notMarked === 1 ? "batch has" : "batches have"} not marked attendance today.
              </p>
            )}
            {[...groups].map(([title, list]) => (
              <Section key={title} title={title}>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {list.map((b) => {
                    const mine = students.filter((s) => s.batch_id === b.id);
                    const c = countStatuses(mine.map((s) => statusOf.get(s.id)));
                    const marked = mine.length > 0 && c.unmarked < mine.length;
                    const done = mine.length > 0 && c.unmarked === 0;
                    return (
                      <Link key={b.id} href={`/attendance/${b.id}`}>
                        <Card className="flex items-center gap-3 p-4 hover:ring-1 hover:ring-primary">
                          <div className="min-w-0 flex-1">
                            <p className="font-bold text-navy">{batchShort(b)}</p>
                            <p className="text-xs text-muted">{mine.length} students</p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {done ? (
                                <Chip tone="ok">
                                  <CheckCircle2 size={12} /> Marked
                                </Chip>
                              ) : marked ? (
                                <Chip tone="warn">
                                  <Clock size={12} /> {c.unmarked} left
                                </Chip>
                              ) : (
                                <Chip tone={mine.length ? "danger" : "neutral"}>Not marked</Chip>
                              )}
                              {marked && (
                                <>
                                  <Chip tone="ok">P {c.P}</Chip>
                                  <Chip tone="danger">A {c.A}</Chip>
                                  <Chip tone="warn">L {c.L}</Chip>
                                </>
                              )}
                            </div>
                          </div>
                          <ChevronRight size={18} className="text-faint" />
                        </Card>
                      </Link>
                    );
                  })}
                </div>
              </Section>
            ))}
            <Section title="Low attendance and absences" action={<SectionLink href="/attendance/low">Open list</SectionLink>}>
              <p className="text-sm text-muted">Students below 75% in the last 30 days, and anyone absent 3 days in a row, with a ready message to the parent.</p>
            </Section>
          </>
        )}
      </Page>
    </>
  );
}
