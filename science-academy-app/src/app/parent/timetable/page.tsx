import { CalendarDays, ClipboardList } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { batchLabel } from "@/lib/batches";
import { clockLabel, dayLabel, todayIst, weekdayOf } from "@/lib/format";
import { testsForBatches, timetableOf } from "@/lib/academics";
import type { Batch } from "@/lib/types";
import { ChildStrip } from "@/components/ChildStrip";
import { Card, Chip, Empty } from "@/components/ui";
import { getT } from "@/lib/i18n/server";
import type { DictKey } from "@/lib/i18n";

const DAY_KEYS: DictKey[] = ["academics.day.1", "academics.day.2", "academics.day.3", "academics.day.4", "academics.day.5", "academics.day.6", "academics.day.7"];

export const metadata = { title: "Timetable" };

/** The child's batch timetable and upcoming tests (own child's batch only). */
export default async function ParentTimetablePage() {
  const { children, child } = await parentContext();
  const { t } = await getT();
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty>{t("academics.noStudentLinked")}</Empty>
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
        <h1 className="text-xl font-extrabold text-navy">{t("academics.ptt.title")}</h1>
        {batch && <p className="mb-3 text-xs text-muted">{batchLabel(batch)}</p>}
        {!batch ? (
          <Empty icon={CalendarDays}>{t("academics.ptt.noBatch")}</Empty>
        ) : (
          <>
            <h2 className="mt-2 mb-2 text-[15px] font-bold text-navy">{t("academics.ptt.upcoming")}</h2>
            {tests.length === 0 ? (
              <Empty icon={ClipboardList}>{t("academics.ptt.noUpcoming")}</Empty>
            ) : (
              <Card className="divide-y divide-line">
                {tests.map((x) => (
                  <div key={x.id} className="flex items-start gap-2 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold">{x.name}</p>
                      <p className="text-xs text-muted">
                        {dayLabel(x.date)}
                        {x.start_time ? ` · ${clockLabel(x.start_time)}` : ""}
                        {x.subject ? ` · ${x.subject}` : ""}
                        {x.max_marks ? ` · ${t("academics.max", { n: Number(x.max_marks) })}` : ""}
                      </p>
                    </div>
                    <Chip tone={x.tag === "School" ? "violet" : "primary"}>{t(x.tag === "School" ? "academics.tag.School" : "academics.tag.Coaching")}</Chip>
                  </div>
                ))}
              </Card>
            )}

            <h2 className="mt-5 mb-2 text-[15px] font-bold text-navy">{t("academics.ptt.thisWeek")}</h2>
            {entries.length === 0 ? (
              <Empty icon={CalendarDays}>{t("academics.ptt.notAdded")}</Empty>
            ) : (
              <div className="space-y-2">
                {order.map((d) => {
                  const list = entries.filter((e) => e.weekday === d);
                  if (!list.length) return null;
                  return (
                    <Card key={d} className="p-3.5">
                      <p className="mb-1.5 text-xs font-extrabold tracking-wide text-navy uppercase">
                        {t(DAY_KEYS[d - 1])}
                        {d === todayNo ? ` · ${t("core.today")}` : ""}
                      </p>
                      <ul className="space-y-1.5">
                        {list.map((e) => (
                          <li key={e.id} className="flex items-center gap-2 text-sm">
                            <span className="w-28 shrink-0 font-semibold text-muted">
                              {clockLabel(e.start_time)}
                              {e.end_time ? `–${clockLabel(e.end_time)}` : ""}
                            </span>
                            <span className="flex-1 font-bold">{e.subject}</span>
                            {e.tag === "School" && <Chip tone="violet">{t("academics.tag.School")}</Chip>}
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
