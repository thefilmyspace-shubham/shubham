import { notFound } from "next/navigation";
import { AlertTriangle, Megaphone } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { batchesFor, batchLabel } from "@/lib/batches";
import { boardName } from "@/lib/ids";
import { WEEKDAYS, clockLabel, dayLabel } from "@/lib/format";
import { getTest, testCoversBatch, timetableOf } from "@/lib/academics";
import { Banner, Card, Page, PageHeader } from "@/components/ui";
import { postToGroups } from "../actions";

export const metadata = { title: "Post to batch group" };

const ERRORS: Record<string, string> = {
  empty: "Write a message and pick at least one batch.",
  fees: "This looks like a fee message. Fee messages are never posted in batch groups; reception sends fee reminders to each parent privately.",
};

/** The separate step after saving a test or timetable change: post it to the parents' batch group. */
export default async function PostPage({ searchParams }: { searchParams: Promise<{ kind?: string; id?: string; batch?: string; error?: string }> }) {
  const viewer = await requireStaff();
  if (!can(viewer, "groups.post_batch")) notFound();
  const sp = await searchParams;
  const visible = await batchesFor(viewer);
  const kind = sp.kind === "test" ? "test" : "timetable";

  let body = "";
  let targets = visible;
  let back = "/timetable/post";
  if (kind === "test") {
    const test = sp.id ? await getTest(sp.id) : null;
    if (!test) notFound();
    targets = visible.filter((b) => testCoversBatch(test, b));
    body = [
      `${test.tag === "School" ? "School exam" : "Test"}: ${test.name}`,
      `${dayLabel(test.date)}${test.start_time ? `, ${clockLabel(test.start_time)}` : ""}`,
      test.subject ? `Subject: ${test.subject}` : "",
      test.max_marks ? `Max marks: ${Number(test.max_marks)}` : "",
      test.tag === "Coaching" ? "Please make sure your child is on time and prepared." : "",
    ]
      .filter(Boolean)
      .join("\n");
    back = `/timetable/post?kind=test&id=${test.id}`;
  } else {
    const batch = visible.find((b) => b.id === sp.batch);
    if (!batch) notFound();
    targets = [batch];
    const entries = await timetableOf([batch.id]);
    const { data: names } = await adminClient().from("users").select("id, name").eq("role", "faculty");
    const fac = new Map(((names ?? []) as { id: string; name: string }[]).map((u) => [u.id, u.name]));
    const lines = WEEKDAYS.map((d, i) => {
      const list = entries.filter((e) => e.weekday === i + 1);
      return list.length ? `${d}: ${list.map((e) => `${clockLabel(e.start_time)} ${e.subject}${e.faculty_id && fac.get(e.faculty_id) ? ` (${fac.get(e.faculty_id)})` : ""}`).join(", ")}` : "";
    }).filter(Boolean);
    body = [`Timetable updated for ${boardName(batch.board)} ${batch.class} · ${batch.name}`, ...lines].join("\n");
    back = `/timetable/post?kind=timetable&batch=${batch.id}`;
  }

  return (
    <>
      <PageHeader title="Post to batch group" subtitle={kind === "test" ? "Test or exam" : "Timetable change"} back="/timetable" />
      <Page>
        <Card className="mx-auto max-w-xl space-y-3 p-5">
          <Banner tone="warn" icon={AlertTriangle}>
            Every parent in the batch can read this. Never write a student&apos;s name with a fee amount. No fee messages here.
          </Banner>
          {sp.error && ERRORS[sp.error] && (
            <Banner tone="danger" icon={AlertTriangle}>
              {ERRORS[sp.error]}
            </Banner>
          )}
          <form action={postToGroups} className="space-y-3">
            <input type="hidden" name="kind" value={kind} />
            <input type="hidden" name="back" value={back} />
            <div>
              <label className="label" htmlFor="body">
                Message
              </label>
              <textarea id="body" name="body" rows={8} defaultValue={body} className="field" required />
            </div>
            <fieldset>
              <legend className="label">Batch groups</legend>
              {targets.length === 0 ? (
                <p className="text-sm text-muted">No batch of yours is covered by this.</p>
              ) : (
                <div className="space-y-1.5">
                  {targets.map((b) => (
                    <label key={b.id} className="flex items-center gap-2 rounded-field bg-field px-3 py-2 text-sm font-semibold">
                      <input type="checkbox" name="batch" value={b.id} defaultChecked className="h-4 w-4 accent-[var(--color-primary)]" />
                      {batchLabel(b)}
                    </label>
                  ))}
                </div>
              )}
            </fieldset>
            <button className="btn btn-primary w-full" disabled={targets.length === 0}>
              <Megaphone size={16} /> Post as {kind === "test" ? "Test" : "Timetable"}
            </button>
          </form>
        </Card>
      </Page>
    </>
  );
}
