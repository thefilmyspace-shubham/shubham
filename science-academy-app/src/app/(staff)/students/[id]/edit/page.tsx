import { notFound } from "next/navigation";
import { requirePermission } from "@/lib/auth";
import { sessionYearFor } from "@/lib/ids";
import { getStudent, nextRollPreview } from "@/lib/students";
import { getT } from "@/lib/i18n/server";
import { Banner, Page, PageHeader } from "@/components/ui";
import { StudentForm } from "../../StudentForm";
import { batchOptions, formInitial } from "../../form-data";
import { markActive, markLeft } from "../../actions";

export const metadata = { title: "Edit student" };

export default async function EditStudentPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ draft?: string }>;
}) {
  await requirePermission("students.edit");
  const { t } = await getT();
  const { id } = await params;
  const { draft } = await searchParams;
  const student = await getStudent(id);
  if (!student) notFound();
  const [batches, nextRoll, initial] = await Promise.all([batchOptions(), nextRollPreview(), formInitial(student)]);
  const isDraft = student.status === "draft";
  return (
    <>
      <PageHeader
        title={isDraft ? t("students.edit.finish") : t("students.edit.title", { name: student.name })}
        subtitle={isDraft ? t("students.edit.draftSub") : student.code}
        back={isDraft ? "/students?status=draft" : `/students/${student.id}`}
      />
      <Page wide>
        {draft && (
          <div className="mb-3">
            <Banner tone="ok">{t("students.edit.draftSaved")}</Banner>
          </div>
        )}
        <StudentForm
          batches={batches}
          nextRoll={nextRoll}
          defaultSession={sessionYearFor(new Date())}
          consentText={t("students.consent.text")}
          initial={initial}
        />
        {student.status === "active" && (
          <form action={markLeft} className="mt-6 flex items-center justify-between gap-3 rounded-card border border-danger-line bg-card p-4">
            <input type="hidden" name="student_id" value={student.id} />
            <p className="text-sm text-muted">{t("students.edit.leftQ")}</p>
            <button className="btn btn-danger shrink-0">{t("students.edit.markLeft")}</button>
          </form>
        )}
        {student.status === "left" && (
          <form action={markActive} className="mt-6 flex items-center justify-between gap-3 rounded-card bg-card p-4 shadow-card">
            <input type="hidden" name="student_id" value={student.id} />
            <p className="text-sm text-muted">{t("students.edit.isLeft")}</p>
            <button className="btn btn-soft shrink-0">{t("students.edit.markActive")}</button>
          </form>
        )}
      </Page>
    </>
  );
}
