import { notFound } from "next/navigation";
import { requirePermission } from "@/lib/auth";
import { sessionYearFor } from "@/lib/ids";
import { CONSENT_TEXT, getStudent, nextRollPreview } from "@/lib/students";
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
  const { id } = await params;
  const { draft } = await searchParams;
  const student = await getStudent(id);
  if (!student) notFound();
  const [batches, nextRoll, initial] = await Promise.all([batchOptions(), nextRollPreview(), formInitial(student)]);
  const isDraft = student.status === "draft";
  return (
    <>
      <PageHeader
        title={isDraft ? "Finish registration" : `Edit ${student.name}`}
        subtitle={isDraft ? "Draft: no ID yet" : student.code}
        back={isDraft ? "/students?status=draft" : `/students/${student.id}`}
      />
      <Page wide>
        {draft && (
          <div className="mb-3">
            <Banner tone="ok">Draft saved. Press Register when everything is filled in and consent is given.</Banner>
          </div>
        )}
        <StudentForm
          batches={batches}
          nextRoll={nextRoll}
          defaultSession={sessionYearFor(new Date())}
          consentText={CONSENT_TEXT}
          initial={initial}
        />
        {student.status === "active" && (
          <form action={markLeft} className="mt-6 flex items-center justify-between gap-3 rounded-card border border-danger-line bg-card p-4">
            <input type="hidden" name="student_id" value={student.id} />
            <p className="text-sm text-muted">Student has left the academy? Their roll number is never given to anyone else.</p>
            <button className="btn btn-danger shrink-0">Mark as left</button>
          </form>
        )}
        {student.status === "left" && (
          <form action={markActive} className="mt-6 flex items-center justify-between gap-3 rounded-card bg-card p-4 shadow-card">
            <input type="hidden" name="student_id" value={student.id} />
            <p className="text-sm text-muted">This student is marked as left.</p>
            <button className="btn btn-soft shrink-0">Mark as active again</button>
          </form>
        )}
      </Page>
    </>
  );
}
