import { notFound } from "next/navigation";
import { CheckCircle2, Info, UserCheck } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { allBatches, batchMap, batchShort } from "@/lib/batches";
import { boardName } from "@/lib/ids";
import { clockLabel, dayLabel } from "@/lib/format";
import { facultyNames, getTest, studentsForTest } from "@/lib/academics";
import { testAccess, testAttendanceOf } from "@/lib/test-duty";
import { Banner, Chip, Empty, Page, PageHeader } from "@/components/ui";
import { getT } from "@/lib/i18n/server";
import { TestAttendanceSheet, type TestAttRow } from "./TestAttendanceSheet";

export const metadata = { title: "Test attendance" };

/** Who came to a test: the faculty on duty (every student), Admin/Management, other faculty (own batches). */
export default async function TestAttendancePage({ params }: { params: Promise<{ id: string }> }) {
  const viewer = await requireStaff();
  const { id } = await params;
  const { t } = await getT();
  const test = await getTest(id);
  if (!test) notFound();
  const access = testAccess(viewer, test);
  if (!access.see) notFound();
  const [students, present, batches, faculty] = await Promise.all([studentsForTest(test, access.scope), testAttendanceOf(test.id), allBatches(true), facultyNames()]);
  const bmap = batchMap(batches);
  const rows: TestAttRow[] = students.map((s) => {
    const b = s.batch_id ? bmap.get(s.batch_id) : undefined;
    const p = present.get(s.id);
    return { id: s.id, name: s.name, code: s.code, batch: b ? batchShort(b) : "", status: p === undefined ? null : p ? "P" : "A" };
  });
  const dutyName = test.faculty_id ? faculty.get(test.faculty_id) : null;
  const canMarks = can(viewer, "marks.enter") || can(viewer, "students.view");

  return (
    <>
      <PageHeader
        title={t("academics.duty.attTitle", { test: test.name })}
        subtitle={`${boardName(test.board)} ${test.class} · ${test.batch_id && bmap.get(test.batch_id) ? batchShort(bmap.get(test.batch_id)!) : t("academics.wholeClass")} · ${dayLabel(test.date)}${test.start_time ? ` · ${clockLabel(test.start_time)}` : ""}`}
        back="/timetable"
      />
      <Page>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {dutyName && (
            <Chip tone="navy">
              <UserCheck size={13} /> {t("academics.duty.onDuty", { name: dutyName })}
            </Chip>
          )}
          {test.done_at && (
            <Chip tone="ok">
              <CheckCircle2 size={13} /> {t("academics.duty.done")}
            </Chip>
          )}
        </div>
        {!access.scope ? null : (
          <div className="mb-3">
            <Banner tone="neutral" icon={Info}>
              {t("academics.duty.ownBatches")}
            </Banner>
          </div>
        )}
        {!access.canRun ? (
          <Banner tone="neutral" icon={Info}>
            {t("academics.duty.noAccess")}
          </Banner>
        ) : rows.length === 0 ? (
          <Empty>{t("academics.marks.noStudents")}</Empty>
        ) : (
          <TestAttendanceSheet testId={test.id} rows={rows} done={Boolean(test.done_at)} marksHref={canMarks ? `/tests/${test.id}` : null} />
        )}
      </Page>
    </>
  );
}
