import Link from "next/link";
import { notFound } from "next/navigation";
import { AlertTriangle, Trash2 } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { allBatches, batchLabel } from "@/lib/batches";
import { BOARDS, CLASSES, boardName } from "@/lib/ids";
import { todayIst } from "@/lib/format";
import { getTest, timeInput } from "@/lib/academics";
import { Banner, Card, Page, PageHeader } from "@/components/ui";
import { deleteTest, saveTest } from "../actions";
import { getT } from "@/lib/i18n/server";
import type { DictKey } from "@/lib/i18n";

export const metadata = { title: "Test or exam" };

const ERRORS: Record<string, DictKey> = {
  form: "academics.test.err.form",
  save: "academics.test.err.save",
  hasmarks: "academics.test.err.hasmarks",
};

/** Add or edit a test or exam (Admin, Management). */
export default async function TestFormPage({ searchParams }: { searchParams: Promise<{ id?: string; for?: string; error?: string }> }) {
  const viewer = await requireStaff();
  if (!can(viewer, "academics.edit")) notFound();
  const sp = await searchParams;
  const { t } = await getT();
  const test = sp.id ? await getTest(sp.id) : null;
  if (sp.id && !test) notFound();
  const batches = await allBatches();
  const forValue = test ? (test.batch_id ? `batch:${test.batch_id}` : `class:${test.board}:${test.class}`) : (sp.for ?? "");

  return (
    <>
      <PageHeader title={test ? t("academics.test.titleEdit") : t("academics.test.titleNew")} subtitle={t("academics.test.sub")} back="/timetable" />
      <Page>
        <Card className="mx-auto max-w-xl p-5">
          {sp.error && ERRORS[sp.error] && (
            <div className="mb-3">
              <Banner tone="danger" icon={AlertTriangle}>
                {t(ERRORS[sp.error])}
              </Banner>
            </div>
          )}
          <form action={saveTest} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {test && <input type="hidden" name="id" value={test.id} />}
            <div className="sm:col-span-2">
              <label className="label" htmlFor="name">
                {t("academics.test.name")}
              </label>
              <input id="name" name="name" required defaultValue={test?.name} placeholder="Unit test 3 · Physics" className="field" />
            </div>
            <div className="sm:col-span-2">
              <label className="label" htmlFor="for">
                {t("academics.test.for")}
              </label>
              <select id="for" name="for" required defaultValue={forValue} className="field">
                <option value="" disabled>
                  {t("academics.test.chooseFor")}
                </option>
                {BOARDS.map((b) => (
                  <optgroup key={b} label={t("academics.test.wholeClassGroup", { board: boardName(b) })}>
                    {CLASSES.map((c) => (
                      <option key={c} value={`class:${b}:${c}`}>
                        {t("academics.test.allBatchesOpt", { board: boardName(b), c })}
                      </option>
                    ))}
                  </optgroup>
                ))}
                <optgroup label={t("academics.test.oneBatch")}>
                  {batches.map((b) => (
                    <option key={b.id} value={`batch:${b.id}`}>
                      {batchLabel(b)}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="subject">
                {t("academics.tt.subject")}
              </label>
              <input id="subject" name="subject" defaultValue={test?.subject ?? ""} placeholder="Physics" className="field" />
            </div>
            <div>
              <label className="label" htmlFor="tag">
                {t("academics.tt.tag")}
              </label>
              <select id="tag" name="tag" defaultValue={test?.tag ?? "Coaching"} className="field">
                <option value="Coaching">{t("academics.test.coachingOpt")}</option>
                <option value="School">{t("academics.test.schoolOpt")}</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="date">
                {t("academics.att.date")}
              </label>
              <input id="date" type="date" name="date" required defaultValue={test?.date ?? todayIst()} className="field" />
            </div>
            <div>
              <label className="label" htmlFor="start_time">
                {t("academics.test.time")}
              </label>
              <input id="start_time" type="time" name="start_time" defaultValue={timeInput(test?.start_time)} className="field" />
            </div>
            <div>
              <label className="label" htmlFor="max_marks">
                {t("academics.test.maxMarks")}
              </label>
              <input id="max_marks" type="number" step="0.5" min="1" name="max_marks" defaultValue={test?.max_marks ?? ""} placeholder="50" className="field" />
            </div>
            <div className="flex items-end gap-2 sm:col-span-2">
              <button className="btn btn-primary flex-1">{test ? t("academics.tt.saveChanges") : t("academics.test.saveTest")}</button>
              <Link href="/timetable" className="btn btn-ghost">
                {t("core.cancel")}
              </Link>
            </div>
          </form>
          <p className="mt-3 text-xs text-muted">{t("academics.test.savingNote")}</p>
          {test && (
            <form action={deleteTest} className="mt-4 border-t border-line pt-4">
              <input type="hidden" name="id" value={test.id} />
              <button className="btn btn-danger py-1.5 text-[13px]">
                <Trash2 size={14} /> {t("academics.test.delete")}
              </button>
            </form>
          )}
        </Card>
      </Page>
    </>
  );
}
