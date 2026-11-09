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

export const metadata = { title: "Test or exam" };

const ERRORS: Record<string, string> = {
  form: "Please fill the name, who it is for, date and tag.",
  save: "Could not save. Please try again.",
  hasmarks: "This test already has marks, so it cannot be deleted. Change it instead.",
};

/** Add or edit a test or exam (Admin, Management). */
export default async function TestFormPage({ searchParams }: { searchParams: Promise<{ id?: string; for?: string; error?: string }> }) {
  const viewer = await requireStaff();
  if (!can(viewer, "academics.edit")) notFound();
  const sp = await searchParams;
  const test = sp.id ? await getTest(sp.id) : null;
  if (sp.id && !test) notFound();
  const batches = await allBatches();
  const forValue = test ? (test.batch_id ? `batch:${test.batch_id}` : `class:${test.board}:${test.class}`) : (sp.for ?? "");

  return (
    <>
      <PageHeader title={test ? "Edit test" : "New test or exam"} subtitle="Tag school exams and coaching tests so they don't clash" back="/timetable" />
      <Page>
        <Card className="mx-auto max-w-xl p-5">
          {sp.error && ERRORS[sp.error] && (
            <div className="mb-3">
              <Banner tone="danger" icon={AlertTriangle}>
                {ERRORS[sp.error]}
              </Banner>
            </div>
          )}
          <form action={saveTest} className="grid gap-3 sm:grid-cols-2">
            {test && <input type="hidden" name="id" value={test.id} />}
            <div className="sm:col-span-2">
              <label className="label" htmlFor="name">
                Name
              </label>
              <input id="name" name="name" required defaultValue={test?.name} placeholder="Unit test 3 · Physics" className="field" />
            </div>
            <div className="sm:col-span-2">
              <label className="label" htmlFor="for">
                For
              </label>
              <select id="for" name="for" required defaultValue={forValue} className="field">
                <option value="" disabled>
                  Choose a class or a batch
                </option>
                {BOARDS.map((b) => (
                  <optgroup key={b} label={`${boardName(b)}: whole class`}>
                    {CLASSES.map((c) => (
                      <option key={c} value={`class:${b}:${c}`}>
                        {boardName(b)} {c} · all batches
                      </option>
                    ))}
                  </optgroup>
                ))}
                <optgroup label="One batch">
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
                Subject
              </label>
              <input id="subject" name="subject" defaultValue={test?.subject ?? ""} placeholder="Physics" className="field" />
            </div>
            <div>
              <label className="label" htmlFor="tag">
                Tag
              </label>
              <select id="tag" name="tag" defaultValue={test?.tag ?? "Coaching"} className="field">
                <option value="Coaching">Coaching (our test)</option>
                <option value="School">School (school exam)</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="date">
                Date
              </label>
              <input id="date" type="date" name="date" required defaultValue={test?.date ?? todayIst()} className="field" />
            </div>
            <div>
              <label className="label" htmlFor="start_time">
                Time
              </label>
              <input id="start_time" type="time" name="start_time" defaultValue={timeInput(test?.start_time)} className="field" />
            </div>
            <div>
              <label className="label" htmlFor="max_marks">
                Max marks
              </label>
              <input id="max_marks" type="number" step="0.5" min="1" name="max_marks" defaultValue={test?.max_marks ?? ""} placeholder="50" className="field" />
            </div>
            <div className="flex items-end gap-2 sm:col-span-2">
              <button className="btn btn-primary flex-1">{test ? "Save changes" : "Save test"}</button>
              <Link href="/timetable" className="btn btn-ghost">
                Cancel
              </Link>
            </div>
          </form>
          <p className="mt-3 text-xs text-muted">Saving does not post anything to parents. Posting to the batch group is a separate step after saving.</p>
          {test && (
            <form action={deleteTest} className="mt-4 border-t border-line pt-4">
              <input type="hidden" name="id" value={test.id} />
              <button className="btn btn-danger py-1.5 text-[13px]">
                <Trash2 size={14} /> Delete test (only if no marks yet)
              </button>
            </form>
          )}
        </Card>
      </Page>
    </>
  );
}
