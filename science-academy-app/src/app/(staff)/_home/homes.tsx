import Link from "next/link";
import { ClipboardCheck, ClipboardX, PhoneCall, ReceiptText, UserPlus } from "lucide-react";
import { can, visibleBatchIds, type StaffViewer } from "@/lib/auth";
import { allBatches, batchesFor, batchLabel, batchMap } from "@/lib/batches";
import { addDays, monthStart, rupees, rupeesShort, todayIst, weekdayOf } from "@/lib/format";
import {
  activeStudents,
  attendanceOn,
  batchMeets,
  callsDue,
  classTop5,
  collected,
  collectionByMonth,
  escalations,
  feeOverview,
  latestCalls,
  lowAttendance,
  reminderChain,
  timetableFor,
  upcomingTests,
} from "@/lib/dashboard";
import { CALL_OUTCOME_LABEL } from "@/lib/fees";
import { Card, Chip, Empty, Section, SectionLink, Stat } from "@/components/ui";
import {
  AttendanceTodayCard,
  ClassToppers,
  CollectionChart,
  LowAttendanceList,
  NeedsAttention,
  PendingByClass,
  ReminderChainCard,
  TodayClasses,
  UpcomingTests,
  type AttentionItem,
} from "./widgets";

/** Admin: the whole academy at a glance (spec §7). */
export async function AdminHome({ viewer }: { viewer: StaffViewer }) {
  const today = todayIst();
  const month = monthStart(today);
  const fees = can(viewer, "fees.view");
  const [students, batches, entries, att] = await Promise.all([activeStudents(), allBatches(), timetableFor(null), attendanceOn(today)]);
  const [feeData, calls, collectedMonth, chart, chain, low, tops] = await Promise.all([
    fees ? feeOverview(today, students) : Promise.resolve(null),
    fees ? latestCalls() : Promise.resolve(null),
    fees ? collected(month, today) : Promise.resolve(0),
    fees ? collectionByMonth(today) : Promise.resolve([]),
    fees ? reminderChain(month) : Promise.resolve({ reminded: 0, called: 0, escalated: 0 }),
    lowAttendance(today, students),
    can(viewer, "ranks.view") ? classTop5(today, students) : Promise.resolve([]),
  ]);
  const bm = batchMap(batches);
  const withStudents = new Set(students.map((s) => s.batch_id));
  const notMarked = batches.filter((b) => withStudents.has(b.id) && batchMeets(b.id, weekdayOf(today), entries) && !att.markedBatches.has(b.id));
  const names = new Map(students.map((s) => [s.id, s]));

  const items: AttentionItem[] = [];
  if (feeData && calls) {
    const due = callsDue(feeData, calls, today);
    for (const d of due.filter((x) => x.reason === "promised_today").slice(0, 5)) {
      const s = names.get(d.studentId);
      items.push({
        key: `p-${d.studentId}`,
        icon: "promise",
        title: `Promised to pay today: ${s?.name ?? ""}`,
        detail: `${s?.code ?? ""} · ${rupees(d.owing.balance)} pending`,
        href: `/fees/${d.studentId}`,
        tone: "primary",
      });
    }
    for (const c of escalations(feeData, calls).slice(0, 5)) {
      const s = names.get(c.student_id);
      items.push({
        key: `e-${c.id}`,
        icon: "escalation",
        title: `Needs admin: ${s?.name ?? ""}`,
        detail: `${rupees(feeData.owing.get(c.student_id)?.balance ?? 0)} pending${c.note ? ` · ${c.note}` : ""}`,
        href: `/fees/${c.student_id}`,
        tone: "danger",
      });
    }
    const overdueCalls = due.filter((x) => x.reason !== "promised_today").length;
    if (overdueCalls) {
      items.push({ key: "calls", icon: "call", title: `${overdueCalls} parent calls due`, detail: "Longest overdue first", href: "/calls", tone: "warn" });
    }
  }
  for (const b of notMarked.slice(0, 6)) {
    items.push({ key: `a-${b.id}`, icon: "attendance", title: `Attendance not marked: ${batchLabel(b)}`, detail: "Today", href: `/attendance/${b.id}`, tone: "warn" });
  }
  const streaks = low.filter((l) => l.absentStreak >= 3);
  if (streaks.length) {
    items.push({
      key: "streak",
      icon: "low",
      title: `${streaks.length} student${streaks.length === 1 ? "" : "s"} absent 3+ days in a row`,
      detail: streaks.slice(0, 3).map((l) => l.student.name).join(", "),
      href: "/attendance",
      tone: "danger",
    });
  }
  const below = low.filter((l) => l.pct < 75).length;
  if (below) items.push({ key: "low", icon: "low", title: `${below} below 75% attendance`, detail: "Last 30 days", href: "/attendance", tone: "warn" });

  return (
    <>
      <div className="grid grid-cols-2 gap-3 pt-4 lg:grid-cols-4">
        <Stat label="Total students" value={students.length} hint={`${batches.length} batches`} href="/students" />
        {feeData && <Stat label="Collected this month" value={rupeesShort(collectedMonth)} tone="ok" hint={rupees(collectedMonth)} href="/fees" />}
        {feeData && <Stat label="Pending amount" value={rupeesShort(feeData.pendingTotal)} tone="danger" hint={`${feeData.owing.size} students`} href="/fees?status=pending" />}
        <Stat label="Attendance today" value={att.total ? `${att.pct}%` : "—"} tone="primary" hint={att.total ? `${att.present + att.late} of ${att.total} present` : "Not marked yet"} href="/attendance" />
      </div>
      <div className="grid gap-x-6 lg:grid-cols-2">
        <div>
          <NeedsAttention items={items} />
          {feeData && <ReminderChainCard chain={chain} overdueStudents={[...feeData.owing.values()].filter((o) => o.overdue > 0).length} />}
        </div>
        <div>
          {feeData && <CollectionChart data={chart} />}
          {feeData && <PendingByClass fees={feeData} />}
        </div>
      </div>
      {can(viewer, "ranks.view") && <ClassToppers tops={tops} />}
      {!feeData && <LowAttendanceList list={low} batches={bm} />}
    </>
  );
}

/** Reception: calls to make, money in today, quick actions. */
export async function ReceptionHome({ viewer }: { viewer: StaffViewer }) {
  const today = todayIst();
  const month = monthStart(today);
  const fees = can(viewer, "fees.view");
  const students = await activeStudents();
  const [feeData, calls, today$, month$, chain, att, batches] = await Promise.all([
    fees ? feeOverview(today, students) : Promise.resolve(null),
    fees ? latestCalls() : Promise.resolve(null),
    fees ? collected(today, today) : Promise.resolve(0),
    fees ? collected(month, today) : Promise.resolve(0),
    fees ? reminderChain(month) : Promise.resolve({ reminded: 0, called: 0, escalated: 0 }),
    attendanceOn(today),
    allBatches(),
  ]);
  const due = feeData && calls ? callsDue(feeData, calls, today) : [];
  const names = new Map(students.map((s) => [s.id, s]));
  const bm = batchMap(batches);

  return (
    <>
      <div className="grid grid-cols-2 gap-3 pt-4 lg:grid-cols-4">
        {feeData && <Stat label="Calls due" value={due.length} tone="danger" hint="Longest overdue first" href="/calls" />}
        {feeData && <Stat label="Collected today" value={rupees(today$)} tone="ok" href="/billing" />}
        {feeData && <Stat label="Collected this month" value={rupeesShort(month$)} tone="ok" hint={rupees(month$)} />}
        {feeData && <Stat label="Pending amount" value={rupeesShort(feeData.pendingTotal)} tone="danger" hint={`${feeData.owing.size} students`} href="/fees" />}
        {!feeData && <Stat label="Students" value={students.length} href="/students" />}
      </div>
      <div className="flex flex-wrap gap-2 pt-4">
        {can(viewer, "bills.create") && (
          <Link href="/billing" className="btn btn-primary">
            <ReceiptText size={17} /> Make bill
          </Link>
        )}
        {can(viewer, "students.edit") && (
          <Link href="/students/new" className="btn btn-green">
            <UserPlus size={17} /> Register student
          </Link>
        )}
        {feeData && (
          <Link href="/calls" className="btn btn-soft">
            <PhoneCall size={17} /> Call log
          </Link>
        )}
      </div>
      <div className="grid gap-x-6 lg:grid-cols-2">
        {feeData && (
          <Section title="Parents to call today" action={<SectionLink href="/calls">Open call log</SectionLink>}>
            {due.length === 0 ? (
              <Empty>No calls due. All fees are on time.</Empty>
            ) : (
              <Card className="divide-y divide-line overflow-hidden">
                {due.slice(0, 7).map((d) => {
                  const s = names.get(d.studentId);
                  return (
                    <Link key={d.studentId} href={`/calls?student=${d.studentId}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-field">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[14px] font-bold">{s?.name}</p>
                        <p className="truncate text-[12.5px] text-muted">
                          {s?.code}
                          {d.lastCall ? ` · last: ${CALL_OUTCOME_LABEL[d.lastCall.outcome]} (attempt ${d.lastCall.attempt_no})` : " · not called yet"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[14px] font-extrabold text-danger">{rupees(d.owing.overdue)}</p>
                        <p className="text-[11.5px] text-muted">{d.reason === "promised_today" ? "Promised today" : `${d.owing.daysLate} days late`}</p>
                      </div>
                    </Link>
                  );
                })}
              </Card>
            )}
          </Section>
        )}
        <div>
          {feeData && <ReminderChainCard chain={chain} overdueStudents={[...feeData.owing.values()].filter((o) => o.overdue > 0).length} />}
          {can(viewer, "students.view") && <AttendanceTodayCard att={att} notMarked={[]} />}
        </div>
      </div>
      {!feeData && <LowAttendanceList list={await lowAttendance(today, students)} batches={bm} />}
    </>
  );
}

/** Management: academics and attendance (no fee data unless Admin gives access). */
export async function ManagementHome({ viewer }: { viewer: StaffViewer }) {
  const today = todayIst();
  const [students, batches, entries, att] = await Promise.all([activeStudents(), allBatches(), timetableFor(null), attendanceOn(today)]);
  const [tests, low, tops, feeData] = await Promise.all([
    upcomingTests(today, 14, null),
    lowAttendance(today, students),
    can(viewer, "ranks.view") ? classTop5(today, students) : Promise.resolve([]),
    can(viewer, "fees.view") ? feeOverview(today, students) : Promise.resolve(null),
  ]);
  const bm = batchMap(batches);
  const withStudents = new Set(students.map((s) => s.batch_id));
  const notMarked = batches.filter((b) => withStudents.has(b.id) && batchMeets(b.id, weekdayOf(today), entries) && !att.markedBatches.has(b.id));
  return (
    <>
      <div className="grid grid-cols-2 gap-3 pt-4 lg:grid-cols-4">
        <Stat label="Students" value={students.length} hint={`${batches.length} batches`} href="/students" />
        <Stat label="Attendance today" value={att.total ? `${att.pct}%` : "—"} tone="primary" hint={att.total ? `${att.absent} absent` : "Not marked yet"} href="/attendance" />
        <Stat label="Tests in 14 days" value={tests.length} tone="navy" href="/timetable" />
        <Stat label="Low attendance" value={low.length} tone={low.length ? "warn" : "ok"} hint="Below 75% or 3 days absent" href="/attendance" />
        {feeData && <Stat label="Pending amount" value={rupeesShort(feeData.pendingTotal)} tone="danger" href="/fees" />}
      </div>
      <div className="grid gap-x-6 lg:grid-cols-2">
        <div>
          <AttendanceTodayCard att={att} notMarked={notMarked} />
          <LowAttendanceList list={low} batches={bm} />
        </div>
        <UpcomingTests tests={tests} batches={bm} />
      </div>
      {can(viewer, "ranks.view") && <ClassToppers tops={tops} />}
    </>
  );
}

/** Faculty: own batches, attendance to mark, today's classes, tests. */
export async function FacultyHome({ viewer }: { viewer: StaffViewer }) {
  const today = todayIst();
  const mine = await batchesFor(viewer);
  const ids = visibleBatchIds(viewer) ?? mine.map((b) => b.id);
  const [students, entries, att, attYesterday, tests] = await Promise.all([
    activeStudents(ids),
    timetableFor(ids),
    attendanceOn(today, ids),
    attendanceOn(addDays(today, -1), ids),
    upcomingTests(today, 14, mine),
  ]);
  const low = await lowAttendance(today, students);
  const bm = batchMap(mine);
  const weekday = weekdayOf(today);
  const todayEntries = entries.filter((e) => e.weekday === weekday);
  const counts = new Map<string, number>();
  for (const s of students) if (s.batch_id) counts.set(s.batch_id, (counts.get(s.batch_id) ?? 0) + 1);

  return (
    <>
      <Section title="My batches" action={can(viewer, "attendance.mark") ? <SectionLink href="/attendance">Attendance</SectionLink> : undefined}>
        {mine.length === 0 ? (
          <Empty>No batches are assigned to you yet. Admin assigns batches in Batches & faculty.</Empty>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {mine.map((b) => {
              const meets = batchMeets(b.id, weekday, entries);
              const marked = att.markedBatches.has(b.id);
              const missedYesterday = batchMeets(b.id, weekdayOf(addDays(today, -1)), entries) && !attYesterday.markedBatches.has(b.id) && (counts.get(b.id) ?? 0) > 0;
              return (
                <Link key={b.id} href={`/attendance/${b.id}`} className="block">
                  <Card className="flex items-center gap-3 p-4 hover:ring-1 hover:ring-primary">
                    <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${marked ? "bg-ok-soft text-ok" : "bg-warn-soft text-warn"}`}>
                      {marked ? <ClipboardCheck size={19} /> : <ClipboardX size={19} />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[14.5px] font-bold">{batchLabel(b)}</p>
                      <p className="text-[12.5px] text-muted">{counts.get(b.id) ?? 0} students</p>
                      {missedYesterday && <p className="text-[12px] font-semibold text-danger">Yesterday not marked</p>}
                    </div>
                    {marked ? <Chip tone="ok">Marked</Chip> : meets ? <Chip tone="warn">Mark today</Chip> : <Chip>No class</Chip>}
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </Section>
      <div className="grid gap-x-6 lg:grid-cols-2">
        <TodayClasses entries={todayEntries} batches={bm} />
        <UpcomingTests tests={tests} batches={bm} title="Upcoming tests for my batches" />
      </div>
      {can(viewer, "students.view") && <LowAttendanceList list={low} batches={bm} />}
    </>
  );
}
