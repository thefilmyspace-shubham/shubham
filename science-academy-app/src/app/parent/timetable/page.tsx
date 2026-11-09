import { CalendarDays, ClipboardList } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { batchLabel } from "@/lib/batches";
import { WEEKDAYS, clockLabel, dayLabel, todayIst, weekdayOf } from "@/lib/format";
import { testsForBatches, timetableOf } from "@/lib/academics";
import type { Batch } from "@/lib/types";
import { ChildStrip } from "@/components/ChildStrip";
import { Card, Chip, Empty } from "@/components/ui";

export const metadata = { title: "Timetable" };

/** The child's batch timetable and upcoming tests (own child's batch only). */
export default async function ParentTimetablePage() {
  const { children, child } = await parentContext();
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty>No student is linked to this login number. Please contact the academy.</Empty>
      </div>
    );
  }
  const today = todayIst();
  const { data: batch } = child.batch_id
    ? await adminClient().from("batches").select("*").eq("id", child.batch_id).maybeSingle<Batch>()
    : { data: null };
  const [entries, tests] = batch ? await Promise.all([timetableOf([batch.id]), testsForBatches([batch], today, 30)]) : [[], []];
  const todayNo = weekdayOf(today);
  // Start the week list from today.
  const order = Array.from({ length: 7 }, (_, i) => ((todayNo - 1 + i) % 7) + 1);

  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent/timetable" />
      <div className="mx-auto max-w-lg px-4 pt-4">
        <h1 className="text-xl font-extrabold text-navy">Timetable</h1>
        {batch && <p className="mb-3 text-xs text-muted">{batchLabel(batch)}</p>}
        {!batch ? (
          <Empty icon={CalendarDays}>No batch assigned yet.</Empty>
        ) : (
          <>
            <h2 className="mt-2 mb-2 text-[15px] font-bold text-navy">Upcoming tests and exams</h2>
            {tests.length === 0 ? (
              <Empty icon={ClipboardList}>No upcoming tests.</Empty>
            ) : (
              <Card className="divide-y divide-line">
                {tests.map((t) => (
                  <div key={t.id} className="flex items-start gap-2 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold">{t.name}</p>
                      <p className="text-xs text-muted">
                        {dayLabel(t.date)}
                        {t.start_time ? ` · ${clockLabel(t.start_time)}` : ""}
                        {t.subject ? ` · ${t.subject}` : ""}
                        {t.max_marks ? ` · Max ${Number(t.max_marks)}` : ""}
                      </p>
                    </div>
                    <Chip tone={t.tag === "School" ? "violet" : "primary"}>{t.tag}</Chip>
                  </div>
                ))}
              </Card>
            )}

            <h2 className="mt-5 mb-2 text-[15px] font-bold text-navy">This week</h2>
            {entries.length === 0 ? (
              <Empty icon={CalendarDays}>The timetable is not added yet.</Empty>
            ) : (
              <div className="space-y-2">
                {order.map((d) => {
                  const list = entries.filter((e) => e.weekday === d);
                  if (!list.length) return null;
                  return (
                    <Card key={d} className="p-3.5">
                      <p className="mb-1.5 text-xs font-extrabold tracking-wide text-navy uppercase">
                        {WEEKDAYS[d - 1]}
                        {d === todayNo ? " · Today" : ""}
                      </p>
                      <ul className="space-y-1.5">
                        {list.map((e) => (
                          <li key={e.id} className="flex items-center gap-2 text-sm">
                            <span className="w-28 shrink-0 font-semibold text-muted">
                              {clockLabel(e.start_time)}
                              {e.end_time ? `–${clockLabel(e.end_time)}` : ""}
                            </span>
                            <span className="flex-1 font-bold">{e.subject}</span>
                            {e.tag === "School" && <Chip tone="violet">School</Chip>}
                          </li>
                        ))}
                      </ul>
                    </Card>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
