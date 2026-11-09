import { requirePermission } from "@/lib/auth";
import { sessionYearFor } from "@/lib/ids";
import { nextRollPreview } from "@/lib/students";
import { getT } from "@/lib/i18n/server";
import { Page, PageHeader } from "@/components/ui";
import { StudentForm } from "../StudentForm";
import { batchOptions } from "../form-data";

export const metadata = { title: "Register student" };

export default async function NewStudentPage() {
  await requirePermission("students.edit");
  const { t } = await getT();
  const [batches, nextRoll] = await Promise.all([batchOptions(), nextRollPreview()]);
  return (
    <>
      <PageHeader title={t("students.register")} subtitle={t("students.new.subtitle")} back="/students" />
      <Page wide>
        <StudentForm batches={batches} nextRoll={nextRoll} defaultSession={sessionYearFor(new Date())} consentText={t("students.consent.text")} />
      </Page>
    </>
  );
}
