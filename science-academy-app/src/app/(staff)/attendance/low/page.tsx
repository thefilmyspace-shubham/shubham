import Link from "next/link";
import { notFound } from "next/navigation";
import { CalendarX, TrendingDown } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { batchesFor, batchMap, batchShort } from "@/lib/batches";
import { boardName } from "@/lib/ids";
import { dateLabel, todayIst } from "@/lib/format";
import { activeStudentsOfBatches } from "@/lib/academics";
import { ABSENT_STREAK_FLAG, LOW_ATTENDANCE_PCT, attendanceBetween, flagsFor, windowStart } from "@/lib/attendance";
import { Card, Chip, Empty, FilterChips, Page, PageHeader } from "@/components/ui";
import { Meter } from "@/components/BarChart";
import { AlertMessage } from "./AlertCard";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Low attendance" };

export default async function LowAttendancePage({ searchParams }: { searchParams: Promise<{ show?: string }> }) {
  const viewer = await requireStaff();
  if (!can(viewer, "students.view")) notFound();
  const { show } = await searchParams;
  const { t } = await getT();
  const today = todayIst();
  const from = windowStart(today, 30);
  const batches = await batchesFor(viewer);
  const bmap = batchMap(batches);
  const students = await activeStudentsOfBatches(batches.map((b) => b.id));
  const rows = await attendanceBetween(
    students.map((s) => s.id),
    from,
    today,
  );
  const flags = flagsFor(rows);
  const flagged = students
    .map((s) => ({ s, f: flags.get(s.id) }))
    .filter((x): x is { s: (typeof students)[number]; f: NonNullable<typeof x.f> } => Boolean(x.f && (x.f.low || x.f.streak >= ABSENT_STREAK_FLAG)))
    .sort((a, b) => b.f.streak - a.f.streak || (a.f.pct ?? 0) - (b.f.pct ?? 0));
  const lowCount = flagged.filter((x) => x.f.low).length;
  const streakCount = flagged.filter((x) => x.f.streak >= ABSENT_STREAK_FLAG).length;
  const list = flagged.filter((x) => (show === "low" ? x.f.low : show === "streak" ? x.f.streak >= ABSENT_STREAK_FLAG : true));

  // The ready message to the parent, with its values (sent in the parent's language if not edited).
  const message = (name: string, code: string | null, pct: number | null, streak: number, streakDates: string[]) => {
    const first = name.split(" ")[0];
    if (streak >= ABSENT_STREAK_FLAG) {
      const params = { name, code: code ?? "", n: streak, dates: streakDates.map((d) => dateLabel(d).replace(/ \d{4}$/, "")).join(", "), first };
      return { kind: "streak" as const, params, text: t("academics.att.msgStreak", params) };
    }
    const params = { name, code: code ?? "", pct: pct ?? 0, min: LOW_ATTENDANCE_PCT, first };
    return { kind: "low" as const, params, text: t("academics.att.msgLow", params) };
  };

  return (
    <>
      <PageHeader title={t("academics.att.lowTitle")} subtitle={t("academics.att.lowSub", { from: dateLabel(from), to: dateLabel(today) })} back="/attendance" />
      <Page>
        <FilterChips
          items={[
            { href: "/attendance/low", label: t("academics.att.allFlags"), count: flagged.length, active: !show },
            { href: "/attendance/low?show=low", label: t("academics.att.below", { pct: LOW_ATTENDANCE_PCT }), count: lowCount, active: show === "low" },
            { href: "/attendance/low?show=streak", label: t("academics.att.streakFilter", { n: ABSENT_STREAK_FLAG }), count: streakCount, active: show === "streak" },
          ]}
        />
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {list.length === 0 ? (
            <div className="lg:col-span-2">
              <Empty icon={TrendingDown}>{t("academics.att.noneFlagged")}</Empty>
            </div>
          ) : (
            list.map(({ s, f }) => {
              const b = s.batch_id ? bmap.get(s.batch_id) : undefined;
              return (
                <Card key={s.id} className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <Link href={`/students/${s.id}`} className="font-bold text-navy hover:underline">
                        {s.name}
                      </Link>
                      <p className="text-xs text-muted">
                        {s.code} · {boardName(s.board)} {s.current_class}
                        {b ? ` · ${batchShort(b)}` : ""}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {f.low && <Chip tone="danger">{t("academics.att.pctAttendance", { pct: f.pct ?? 0 })}</Chip>}
                      {f.streak >= ABSENT_STREAK_FLAG && (
                        <Chip tone="warn">
                          <CalendarX size={12} /> {t("academics.att.absentRow", { n: f.streak })}
                        </Chip>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2 text-xs text-muted">
                    <Meter value={f.pct ?? 0} tone={f.low ? "danger" : "ok"} />
                    <span className="shrink-0">{t("academics.att.daysMarked", { n: f.days })}</span>
                  </div>
                  {(() => {
                    const m = message(s.name, s.code, f.pct, f.streak, f.streakDates);
                    return <AlertMessage studentId={s.id} message={m.text} kind={m.kind} params={m.params} />;
                  })()}
                </Card>
              );
            })
          )}
        </div>
      </Page>
    </>
  );
}
