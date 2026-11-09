import Link from "next/link";
import { notFound } from "next/navigation";
import { Info, Trophy } from "lucide-react";
import { can, canSeeBatch, requireStaff, visibleBatchIds } from "@/lib/auth";
import { allBatches, batchMap, batchShort } from "@/lib/batches";
import { boardName } from "@/lib/ids";
import { dayLabel } from "@/lib/format";
import { classSummary, getTest, marksOf, studentsForTest } from "@/lib/academics";
import { Banner, Chip, Empty, Page, PageHeader } from "@/components/ui";
import { MarksForm, type MarksRow } from "./MarksForm";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Marks" };

export default async function TestMarksPage({ params }: { params: Promise<{ id: string }> }) {
  const viewer = await requireStaff();
  const { id } = await params;
  const { t } = await getT();
  const canEnter = can(viewer, "marks.enter");
  if (!canEnter && !can(viewer, "students.view")) notFound();
  const test = await getTest(id);
  if (!test) notFound();
  if (test.batch_id && !canSeeBatch(viewer, test.batch_id)) notFound();
  const students = await studentsForTest(test, visibleBatchIds(viewer));
  if (!students.length && viewer.user.role === "faculty") notFound();
  const [marks, batches] = await Promise.all([marksOf([test.id]), allBatches(true)]);
  const bmap = batchMap(batches);
  const byStudent = new Map(marks.map((m) => [m.student_id, m]));
  const max = test.max_marks === null ? null : Number(test.max_marks);

  const rows: MarksRow[] = students.map((s) => {
    const m = byStudent.get(s.id);
    const b = s.batch_id ? bmap.get(s.batch_id) : undefined;
    return { id: s.id, name: s.name, code: s.code, batch: b ? batchShort(b) : "", score: m?.score ?? null, absent: m?.absent ?? false };
  });
  const entered = rows.filter((r) => r.score !== null || r.absent).length;
  const summary = classSummary(
    rows.map((r) => ({ studentId: r.id, score: r.score, absent: r.absent })),
    max,
  );

  return (
    <>
      <PageHeader
        title={test.name}
        subtitle={`${boardName(test.board)} ${test.class} · ${test.batch_id && bmap.get(test.batch_id) ? batchShort(bmap.get(test.batch_id)!) : t("academics.wholeClass")} · ${dayLabel(test.date)}${max !== null ? ` · ${t("academics.max", { n: max })}` : ""}`}
        back="/timetable"
        right={
          can(viewer, "ranks.view") ? (
            <Link href={`/ranks?test=${test.id}`} className="btn btn-ghost py-1.5 text-[13px]">
              <Trophy size={15} /> {t("academics.marks.ranks")}
            </Link>
          ) : null
        }
      />
      <Page>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Chip tone={test.tag === "School" ? "violet" : "primary"}>{t(test.tag === "School" ? "academics.tag.School" : "academics.tag.Coaching")}</Chip>
          {test.subject && <Chip>{test.subject}</Chip>}
          <Chip tone={entered === rows.length && rows.length ? "ok" : "warn"}>
            {t("academics.marks.enteredOf", { n: entered, total: rows.length })}
          </Chip>
          {summary.average !== null && <Chip tone="navy">{t("academics.marks.average", { n: summary.average })}</Chip>}
        </div>
        {max === null && (
          <div className="mb-3">
            <Banner tone="warn" icon={Info}>
              {t("academics.marks.noMax")}
            </Banner>
          </div>
        )}
        {viewer.user.role === "faculty" && !test.batch_id && (
          <div className="mb-3">
            <Banner tone="neutral" icon={Info}>
              {t("academics.marks.facultyWhole")}
            </Banner>
          </div>
        )}
        {!canEnter && (
          <div className="mb-3">
            <Banner tone="neutral" icon={Info}>
              {t("academics.marks.viewOnly")}
            </Banner>
          </div>
        )}
        {rows.length === 0 ? <Empty>{t("academics.marks.noStudents")}</Empty> : <MarksForm testId={test.id} max={max} rows={rows} readOnly={!canEnter} />}
      </Page>
    </>
  );
}
