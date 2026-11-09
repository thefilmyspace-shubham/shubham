import { requirePermission } from "@/lib/auth";
import { sessionYearFor } from "@/lib/ids";
import { CONSENT_TEXT, nextRollPreview } from "@/lib/students";
import { Page, PageHeader } from "@/components/ui";
import { StudentForm } from "../StudentForm";
import { batchOptions } from "../form-data";

export const metadata = { title: "Register student" };

export default async function NewStudentPage() {
  await requirePermission("students.edit");
  const [batches, nextRoll] = await Promise.all([batchOptions(), nextRollPreview()]);
  return (
    <>
      <PageHeader title="Register student" subtitle="The ID is created when you press Register" back="/students" />
      <Page wide>
        <StudentForm batches={batches} nextRoll={nextRoll} defaultSession={sessionYearFor(new Date())} consentText={CONSENT_TEXT} />
      </Page>
    </>
  );
}
