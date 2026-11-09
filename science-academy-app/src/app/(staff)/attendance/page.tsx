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
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Attendance" };

export default async function AttendancePage() {
  const viewer = await requireStaff();
  if (!can(viewer, "attendance.mark") && !can(viewer, "students.view")) notFound();
  const canMark = can(viewer, "attendance.mark");
  const { t } = await getT();
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
    const k = `${boardName(b.board)} · ${t("academics.class", { n: b.class })}`;
    groups.set(k, [...(groups.get(k) ?? []), b]);
  }
  const notMarked = batches.filter((b) => {
    const list = students.filter((s) => s.batch_id === b.id);
    return list.length > 0 && list.every((s) => !statusOf.has(s.id));
  }).length;

  return (
    <>
      <PageHeader
        title={t("academics.att.title")}
        subtitle={`${t("academics.att.todaySub", { date: dayLabel(today) })}${canMark ? "" : t("academics.att.viewOnlySuffix")}`}
        right={
          <Link href="/attendance/low" className="btn btn-ghost py-1.5 text-[13px]">
            <AlertTriangle size={15} /> {t("academics.att.lowBtn")}
          </Link>
        }
      />
      <Page>
        {batches.length === 0 ? (
          <Empty icon={ClipboardCheck}>
            {viewer.user.role === "faculty" ? t("academics.att.noBatchesFaculty") : t("academics.att.noBatches")}
          </Empty>
        ) : (
          <>
            {notMarked > 0 && (
              <p className="mb-1 text-sm font-semibold text-warn">
                {t(notMarked === 1 ? "academics.att.notMarked1" : "academics.att.notMarkedN", { n: notMarked })}
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
                            <p className="text-xs text-muted">{t("academics.students", { n: mine.length })}</p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {done ? (
                                <Chip tone="ok">
                                  <CheckCircle2 size={12} /> {t("academics.att.marked")}
                                </Chip>
                              ) : marked ? (
                                <Chip tone="warn">
                                  <Clock size={12} /> {t("academics.att.left", { n: c.unmarked })}
                                </Chip>
                              ) : (
                                <Chip tone={mine.length ? "danger" : "neutral"}>{t("academics.att.notMarked")}</Chip>
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
            <Section title={t("academics.att.lowSection")} action={<SectionLink href="/attendance/low">{t("academics.att.openList")}</SectionLink>}>
              <p className="text-sm text-muted">{t("academics.att.lowSectionText")}</p>
            </Section>
          </>
        )}
      </Page>
    </>
  );
}
