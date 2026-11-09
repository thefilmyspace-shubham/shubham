import Link from "next/link";
import { AlertTriangle, BellRing, CalendarClock, ChevronRight, ClipboardX, PhoneCall, Trophy, UserX } from "lucide-react";
import { BarChart, Meter } from "@/components/BarChart";
import { Card, Chip, Empty, Section, SectionLink } from "@/components/ui";
import { boardName } from "@/lib/ids";
import { clockLabel, dayLabel, monthShort, rupees, rupeesShort } from "@/lib/format";
import { batchLabel } from "@/lib/batches";
import type { ClassTop, DayAttendance, FeeOverview, LowAttendance } from "@/lib/dashboard";
import type { Batch, Test, TimetableEntry } from "@/lib/types";

export type AttentionItem = {
  key: string;
  icon: "call" | "escalation" | "attendance" | "low" | "promise";
  title: string;
  detail?: string;
  href: string;
  tone: "danger" | "warn" | "primary";
};

const ATTENTION_ICON = { call: PhoneCall, escalation: AlertTriangle, attendance: ClipboardX, low: UserX, promise: BellRing };

export function NeedsAttention({ items }: { items: AttentionItem[] }) {
  return (
    <Section title="Needs attention today">
      {items.length === 0 ? (
        <Empty>All clear for today.</Empty>
      ) : (
        <Card className="divide-y divide-line overflow-hidden">
          {items.map((i) => {
            const Icon = ATTENTION_ICON[i.icon];
            const tone = { danger: "bg-danger-soft text-danger", warn: "bg-warn-soft text-warn", primary: "bg-primary-soft text-primary" }[i.tone];
            return (
              <Link key={i.key} href={i.href} className="flex items-center gap-3 px-4 py-2.5 hover:bg-field">
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${tone}`}>
                  <Icon size={17} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14px] font-bold">{i.title}</span>
                  {i.detail && <span className="block truncate text-[12.5px] text-muted">{i.detail}</span>}
                </span>
                <ChevronRight size={17} className="shrink-0 text-faint" />
              </Link>
            );
          })}
        </Card>
      )}
    </Section>
  );
}

export function CollectionChart({ data }: { data: { month: string; amount: number }[] }) {
  return (
    <Section title="Fee collection, last six months" action={<SectionLink href="/fees">Fees</SectionLink>}>
      <Card className="p-4">
        <BarChart data={data.map((d) => ({ label: monthShort(d.month), value: d.amount }))} format={rupeesShort} color="var(--color-primary)" />
      </Card>
    </Section>
  );
}

export function ReminderChainCard({ chain, overdueStudents }: { chain: { reminded: number; called: number; escalated: number }; overdueStudents: number }) {
  const steps = [
    { label: "Overdue", value: overdueStudents, tone: "text-danger" },
    { label: "Reminded", value: chain.reminded, tone: "text-primary" },
    { label: "Called", value: chain.called, tone: "text-warn" },
    { label: "Escalated", value: chain.escalated, tone: "text-violet" },
  ];
  return (
    <Section title="Fee reminder chain, this month" action={<SectionLink href="/calls">Call log</SectionLink>}>
      <Card className="grid grid-cols-4 divide-x divide-line p-0">
        {steps.map((s) => (
          <div key={s.label} className="px-2 py-3 text-center">
            <p className={`text-xl font-extrabold ${s.tone}`}>{s.value}</p>
            <p className="text-[11.5px] font-semibold text-muted">{s.label}</p>
          </div>
        ))}
      </Card>
      <p className="mt-1.5 text-[11.5px] text-muted">Reminders go to each parent privately. Fee messages are never posted in batch groups.</p>
    </Section>
  );
}

export function PendingByClass({ fees }: { fees: FeeOverview }) {
  const max = Math.max(1, ...fees.byClass.map((c) => c.amount));
  return (
    <Section title="Pending fees by class" action={<SectionLink href="/fees?status=pending">See all</SectionLink>}>
      {fees.byClass.length === 0 ? (
        <Empty>No pending fees.</Empty>
      ) : (
        <Card className="space-y-2.5 p-4">
          {fees.byClass.map((c) => (
            <div key={`${c.board}${c.cls}`}>
              <div className="mb-1 flex items-baseline justify-between gap-2 text-[13px]">
                <span className="font-bold">
                  {boardName(c.board)} {c.cls}
                </span>
                <span className="text-muted">
                  <span className="font-bold text-fg">{rupees(c.amount)}</span> · {c.students} student{c.students === 1 ? "" : "s"}
                </span>
              </div>
              <Meter value={c.amount} max={max} tone="danger" />
            </div>
          ))}
        </Card>
      )}
    </Section>
  );
}

export function ClassToppers({ tops }: { tops: ClassTop[] }) {
  return (
    <Section title="Class-wise top 5" action={<SectionLink href="/ranks">Ranks</SectionLink>}>
      {tops.length === 0 ? (
        <Empty icon={Trophy}>No marks entered yet.</Empty>
      ) : (
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 lg:mx-0 lg:grid lg:grid-cols-2 lg:overflow-visible lg:px-0 xl:grid-cols-3">
          {tops.map((c) => (
            <Card key={`${c.board}${c.cls}`} className="w-72 shrink-0 snap-start p-4 lg:w-auto">
              <div className="mb-2 flex items-baseline justify-between gap-2">
                <p className="font-extrabold text-navy">
                  {boardName(c.board)} {c.cls}
                </p>
                <p className="truncate text-[11.5px] text-muted">
                  {c.test.name} · {dayLabel(c.test.date)}
                </p>
              </div>
              <ol className="space-y-1.5">
                {c.top.map((t, i) => (
                  <li key={t.student.id} className="flex items-center gap-2 text-[13.5px]">
                    <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11.5px] font-extrabold ${i === 0 ? "bg-warn-soft text-warn" : "bg-field text-muted"}`}>
                      {i + 1}
                    </span>
                    <Link href={`/students/${t.student.id}`} className="min-w-0 flex-1 truncate font-semibold hover:text-primary">
                      {t.student.name}
                    </Link>
                    <span className="font-bold">
                      {t.score}
                      {c.test.max_marks ? <span className="font-medium text-muted">/{Number(c.test.max_marks)}</span> : null}
                    </span>
                  </li>
                ))}
              </ol>
            </Card>
          ))}
        </div>
      )}
    </Section>
  );
}

export function AttendanceTodayCard({ att, notMarked, href = "/attendance" }: { att: DayAttendance; notMarked: Batch[]; href?: string }) {
  return (
    <Section title="Attendance today" action={<SectionLink href={href}>Open</SectionLink>}>
      <Card className="p-4">
        {att.total === 0 ? (
          <p className="text-sm text-muted">Not marked yet today.</p>
        ) : (
          <>
            <div className="mb-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-ok">{att.pct}%</span>
              <span className="text-[13px] text-muted">present</span>
            </div>
            <Meter value={att.pct} tone={att.pct >= 75 ? "ok" : "warn"} />
            <div className="mt-2 flex gap-3 text-[12.5px] text-muted">
              <span>
                <b className="text-ok">{att.present}</b> present
              </span>
              <span>
                <b className="text-warn">{att.late}</b> late
              </span>
              <span>
                <b className="text-danger">{att.absent}</b> absent
              </span>
            </div>
          </>
        )}
        {notMarked.length > 0 && (
          <p className="mt-2 text-[12.5px] font-semibold text-warn">
            Not marked: {notMarked.slice(0, 4).map((b) => batchLabel(b)).join(", ")}
            {notMarked.length > 4 ? ` +${notMarked.length - 4} more` : ""}
          </p>
        )}
      </Card>
    </Section>
  );
}

export function UpcomingTests({ tests, batches, title = "Upcoming tests and exams" }: { tests: Test[]; batches: Map<string, Batch>; title?: string }) {
  return (
    <Section title={title} action={<SectionLink href="/timetable">Timetable</SectionLink>}>
      {tests.length === 0 ? (
        <Empty icon={CalendarClock}>No tests in the next two weeks.</Empty>
      ) : (
        <Card className="divide-y divide-line overflow-hidden">
          {tests.slice(0, 8).map((t) => {
            const b = t.batch_id ? batches.get(t.batch_id) : undefined;
            return (
              <div key={t.id} className="flex items-center gap-3 px-4 py-2.5">
                <div className="w-14 shrink-0 text-center">
                  <p className="text-[11px] font-bold text-muted uppercase">{dayLabel(t.date).split(",")[0]}</p>
                  <p className="text-[15px] font-extrabold text-navy">{dayLabel(t.date).split(", ")[1]}</p>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-bold">
                    {t.name}
                    {t.subject ? ` · ${t.subject}` : ""}
                  </p>
                  <p className="truncate text-[12.5px] text-muted">
                    {b ? batchLabel(b) : `${boardName(t.board)} ${t.class} · whole class`}
                    {t.start_time ? ` · ${clockLabel(t.start_time)}` : ""}
                  </p>
                </div>
                <Chip tone={t.tag === "School" ? "violet" : "primary"}>{t.tag}</Chip>
              </div>
            );
          })}
        </Card>
      )}
    </Section>
  );
}

export function LowAttendanceList({ list, batches }: { list: LowAttendance[]; batches: Map<string, Batch> }) {
  return (
    <Section title="Low attendance and repeated absence" action={<SectionLink href="/attendance">Attendance</SectionLink>}>
      {list.length === 0 ? (
        <Empty>Nobody below 75% in the last 30 days.</Empty>
      ) : (
        <Card className="divide-y divide-line overflow-hidden">
          {list.slice(0, 8).map((l) => {
            const b = l.student.batch_id ? batches.get(l.student.batch_id) : undefined;
            return (
              <Link key={l.student.id} href={`/students/${l.student.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-field">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-bold">{l.student.name}</p>
                  <p className="truncate text-[12.5px] text-muted">
                    {l.student.code}
                    {b ? ` · ${batchLabel(b)}` : ""}
                  </p>
                </div>
                {l.absentStreak >= 3 && <Chip tone="danger">Absent {l.absentStreak} days in a row</Chip>}
                <Chip tone={l.pct < 75 ? "warn" : "neutral"}>{l.pct}%</Chip>
              </Link>
            );
          })}
          {list.length > 8 && <p className="px-4 py-2 text-[12.5px] text-muted">+{list.length - 8} more</p>}
        </Card>
      )}
    </Section>
  );
}

export function TodayClasses({ entries, batches }: { entries: TimetableEntry[]; batches: Map<string, Batch> }) {
  return (
    <Section title="Today's classes" action={<SectionLink href="/timetable">Week</SectionLink>}>
      {entries.length === 0 ? (
        <Empty icon={CalendarClock}>No classes on the timetable today.</Empty>
      ) : (
        <Card className="divide-y divide-line overflow-hidden">
          {entries.map((e) => {
            const b = batches.get(e.batch_id);
            return (
              <div key={e.id} className="flex items-center gap-3 px-4 py-2.5">
                <p className="w-20 shrink-0 text-[13px] font-extrabold text-navy">{clockLabel(e.start_time)}</p>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-bold">{e.subject}</p>
                  <p className="truncate text-[12.5px] text-muted">{b ? batchLabel(b) : ""}</p>
                </div>
                <Chip tone={e.tag === "School" ? "violet" : "primary"}>{e.tag}</Chip>
              </div>
            );
          })}
        </Card>
      )}
    </Section>
  );
}
