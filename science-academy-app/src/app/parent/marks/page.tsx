import { Trophy } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { dateLabel } from "@/lib/format";
import { percentOf } from "@/lib/academics";
import type { Test } from "@/lib/types";
import { ChildStrip } from "@/components/ChildStrip";
import { Card, Chip, Empty } from "@/components/ui";

export const metadata = { title: "Marks" };

/** The child's test marks (own child only). */
export default async function ParentMarksPage() {
  const { children, child } = await parentContext();
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty>No student is linked to this login number. Please contact the academy.</Empty>
      </div>
    );
  }
  const { data } = await adminClient()
    .from("marks")
    .select("score, absent, tests!inner(id, name, subject, date, tag, max_marks, board, class)")
    .eq("student_id", child.id);
  type Row = { score: number | null; absent: boolean; tests: Pick<Test, "id" | "name" | "subject" | "date" | "tag" | "max_marks"> };
  const rows = ((data ?? []) as unknown as Row[]).sort((a, b) => b.tests.date.localeCompare(a.tests.date));
  const pcts = rows.map((r) => (r.absent ? null : percentOf(r.score, r.tests.max_marks))).filter((p): p is number => p !== null);
  const avg = pcts.length ? Math.round((pcts.reduce((a, b) => a + b, 0) / pcts.length) * 10) / 10 : null;

  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent/marks" />
      <div className="mx-auto max-w-lg px-4 pt-4">
        <div className="mb-3 flex items-baseline justify-between">
          <h1 className="text-xl font-extrabold text-navy">Marks</h1>
          {avg !== null && <Chip tone="navy">Average {avg}%</Chip>}
        </div>
        {rows.length === 0 ? (
          <Empty icon={Trophy}>No marks yet. You get a notification when a result is added.</Empty>
        ) : (
          <Card className="divide-y divide-line">
            {rows.map((r) => {
              const pct = r.absent ? null : percentOf(r.score, r.tests.max_marks);
              return (
                <div key={r.tests.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-bold">{r.tests.name}</p>
                    <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
                      {dateLabel(r.tests.date)}
                      {r.tests.subject ? ` · ${r.tests.subject}` : ""}
                      <Chip tone={r.tests.tag === "School" ? "violet" : "primary"}>{r.tests.tag}</Chip>
                    </p>
                  </div>
                  <div className="text-right">
                    {r.absent ? (
                      <Chip tone="danger">Absent</Chip>
                    ) : (
                      <>
                        <p className="font-extrabold text-navy">
                          {Number(r.score)}
                          {r.tests.max_marks ? <span className="text-xs font-semibold text-muted"> / {Number(r.tests.max_marks)}</span> : null}
                        </p>
                        {pct !== null && <p className={`text-xs font-bold ${pct >= 75 ? "text-ok" : pct >= 60 ? "text-warn" : "text-danger"}`}>{pct}%</p>}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </Card>
        )}
      </div>
    </>
  );
}
