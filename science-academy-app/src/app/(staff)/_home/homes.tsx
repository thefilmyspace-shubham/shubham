import Link from "next/link";
import { ClipboardCheck, ClipboardX, PhoneCall, ReceiptText, UserCheck, UserPlus } from "lucide-react";
import { dutyTests } from "@/lib/test-duty";
import { boardName } from "@/lib/ids";
import { can, visibleBatchIds, type StaffViewer } from "@/lib/auth";
import { allBatches, batchesFor, batchLabel, batchMap } from "@/lib/batches";
import { addDays, clockLabel, dayLabel, monthStart, rupees, rupeesShort, todayIst, weekdayOf } from "@/lib/format";
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
import { getT } from "@/lib/i18n/server";
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
  const { t } = await getT();
  const today = todayIst();
  const month = monthStart(today);
  const fees = can(viewer, "fees.view");
  const [students, batches, entries, att] = await Promise.all([activeStudents(), allBatches(), timetableFor(null), attendanceOn(today)]);
  const [feeData, calls, collectedMonth, chart, chain, low, tops, tests] = await Promise.all([
    fees ? feeOverview(today, students) : Promise.resolve(null),
    fees ? latestCalls() : Promise.resolve(null),
    fees ? collected(month, today) : Promise.resolve(0),
    fees ? collectionByMonth(today) : Promise.resolve([]),
    fees ? reminderChain(month) : Promise.resolve({ reminded: 0, called: 0, escalated: 0 }),
    lowAttendance(today, students),
    can(viewer, "ranks.view") ? classTop5(today, students) : Promise.resolve([]),
    upcomingTests(today, 14, null),
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
        title: t("admin.home.promisedToday", { name: s?.name ?? "" }),
        detail: `${s?.code ?? ""} · ${t("admin.home.pendingAmount", { amount: rupees(d.owing.balance) })}`,
        href: `/fees/${d.studentId}`,
        tone: "primary",
      });
    }
    for (const c of escalations(feeData, calls).slice(0, 5)) {
      const s = names.get(c.student_id);
      items.push({
        key: `e-${c.id}`,
        icon: "escalation",
        title: t("admin.home.needsAdmin", { name: s?.name ?? "" }),
        detail: `${t("admin.home.pendingAmount", { amount: rupees(feeData.owing.get(c.student_id)?.balance ?? 0) })}${c.note ? ` · ${c.note}` : ""}`,
        href: `/fees/${c.student_id}`,
        tone: "danger",
      });
    }
    const overdueCalls = due.filter((x) => x.reason !== "promised_today").length;
    if (overdueCalls) {
      items.push({ key: "calls", icon: "call", title: t("admin.home.callsDueN", { n: overdueCalls }), detail: t("admin.home.longestFirst"), href: "/calls", tone: "warn" });
    }
  }
  for (const b of notMarked.slice(0, 6)) {
    items.push({ key: `a-${b.id}`, icon: "attendance", title: t("admin.home.attNotMarked", { batch: batchLabel(b) }), detail: t("core.today"), href: `/attendance/${b.id}`, tone: "warn" });
  }
  const streaks = low.filter((l) => l.absentStreak >= 3);
  if (streaks.length) {
    items.push({
      key: "streak",
      icon: "low",
      title: t("admin.home.streakN", { n: streaks.length }),
      detail: streaks.slice(0, 3).map((l) => l.student.name).join(", "),
      href: "/attendance",
      tone: "danger",
    });
  }
  const below = low.filter((l) => l.pct < 75).length;
  if (below) items.push({ key: "low", icon: "low", title: t("admin.home.belowN", { n: below }), detail: t("admin.home.last30"), href: "/attendance", tone: "warn" });

  return (
    <>
      <div className="grid grid-cols-2 gap-3 pt-4 lg:grid-cols-4">
        <Stat label={t("admin.home.totalStudents")} value={students.length} hint={t("admin.home.nBatches", { n: batches.length })} href="/students" />
        {feeData && <Stat label={t("admin.home.collectedMonth")} value={rupeesShort(collectedMonth)} tone="ok" hint={rupees(collectedMonth)} href="/fees" />}
        {feeData && (
          <Stat label={t("admin.home.pending")} value={rupeesShort(feeData.pendingTotal)} tone="danger" hint={t("admin.home.nStudents", { n: feeData.owing.size })} href="/fees?status=pending" />
        )}
        <Stat
          label={t("admin.home.attToday")}
          value={att.total ? `${att.pct}%` : "—"}
          tone="primary"
          hint={att.total ? t("admin.home.presentOf", { n: att.present + att.late, total: att.total }) : t("admin.home.notMarkedYet")}
          href="/attendance"
        />
      </div>
      <div className="grid grid-cols-1 gap-x-6 lg:grid-cols-2">
        <div>
          <NeedsAttention items={items} t={t} />
          {feeData && <ReminderChainCard chain={chain} overdueStudents={[...feeData.owing.values()].filter((o) => o.overdue > 0).length} t={t} />}
        </div>
        <div>
          {feeData && <CollectionChart data={chart} t={t} />}
          {feeData && <PendingByClass fees={feeData} t={t} />}
          <UpcomingTests tests={tests} batches={bm} t={t} />
        </div>
      </div>
      {can(viewer, "ranks.view") && <ClassToppers tops={tops} t={t} />}
      {!feeData && <LowAttendanceList list={low} batches={bm} t={t} />}
    </>
  );
}

/** Reception: calls to make, money in today, quick actions. */
export async function ReceptionHome({ viewer }: { viewer: StaffViewer }) {
  const { t } = await getT();
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
        {feeData && <Stat label={t("admin.home.callsDue")} value={due.length} tone="danger" hint={t("admin.home.longestFirst")} href="/calls" />}
        {feeData && <Stat label={t("admin.home.collectedToday")} value={rupees(today$)} tone="ok" href="/billing" />}
        {feeData && <Stat label={t("admin.home.collectedMonth")} value={rupeesShort(month$)} tone="ok" hint={rupees(month$)} />}
        {feeData && (
          <Stat label={t("admin.home.pending")} value={rupeesShort(feeData.pendingTotal)} tone="danger" hint={t("admin.home.nStudents", { n: feeData.owing.size })} href="/fees" />
        )}
        {!feeData && <Stat label={t("admin.home.students")} value={students.length} href="/students" />}
      </div>
      <div className="flex flex-wrap gap-2 pt-4">
        {can(viewer, "bills.create") && (
          <Link href="/billing" className="btn btn-primary">
            <ReceiptText size={17} /> {t("admin.home.makeBill")}
          </Link>
        )}
        {can(viewer, "students.edit") && (
          <Link href="/students/new" className="btn btn-green">
            <UserPlus size={17} /> {t("admin.home.register")}
          </Link>
        )}
        {feeData && (
          <Link href="/calls" className="btn btn-soft">
            <PhoneCall size={17} /> {t("admin.home.callLog")}
          </Link>
        )}
      </div>
      <div className="grid grid-cols-1 gap-x-6 lg:grid-cols-2">
        {feeData && (
          <Section title={t("admin.home.toCallToday")} action={<SectionLink href="/calls">{t("admin.home.openCallLog")}</SectionLink>}>
            {due.length === 0 ? (
              <Empty>{t("admin.home.noCalls")}</Empty>
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
                          {d.lastCall
                            ? ` · ${t("admin.home.lastCall", { outcome: t(`admin.home.outcome.${d.lastCall.outcome}`), n: d.lastCall.attempt_no })}`
                            : ` · ${t("admin.home.notCalled")}`}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[14px] font-extrabold text-danger">{rupees(d.owing.overdue)}</p>
                        <p className="text-[11.5px] text-muted">{d.reason === "promised_today" ? t("admin.home.promisedTodayShort") : t("admin.home.daysLate", { n: d.owing.daysLate })}</p>
                      </div>
                    </Link>
                  );
                })}
              </Card>
            )}
          </Section>
        )}
        <div>
          {feeData && <ReminderChainCard chain={chain} overdueStudents={[...feeData.owing.values()].filter((o) => o.overdue > 0).length} t={t} />}
          {can(viewer, "students.view") && <AttendanceTodayCard att={att} notMarked={[]} t={t} />}
        </div>
      </div>
      {!feeData && <LowAttendanceList list={await lowAttendance(today, students)} batches={bm} t={t} />}
    </>
  );
}

/** Management: academics and attendance (no fee data unless Admin gives access). */
export async function ManagementHome({ viewer }: { viewer: StaffViewer }) {
  const { t } = await getT();
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
        <Stat label={t("admin.home.students")} value={students.length} hint={t("admin.home.nBatches", { n: batches.length })} href="/students" />
        <Stat
          label={t("admin.home.attToday")}
          value={att.total ? `${att.pct}%` : "—"}
          tone="primary"
          hint={att.total ? t("admin.home.absentN", { n: att.absent }) : t("admin.home.notMarkedYet")}
          href="/attendance"
        />
        <Stat label={t("admin.home.tests14")} value={tests.length} tone="navy" href="/timetable" />
        <Stat label={t("admin.home.lowAtt")} value={low.length} tone={low.length ? "warn" : "ok"} hint={t("admin.home.lowAttHint")} href="/attendance" />
        {feeData && <Stat label={t("admin.home.pending")} value={rupeesShort(feeData.pendingTotal)} tone="danger" href="/fees" />}
      </div>
      <div className="grid grid-cols-1 gap-x-6 lg:grid-cols-2">
        <div>
          <AttendanceTodayCard att={att} notMarked={notMarked} t={t} />
          <LowAttendanceList list={low} batches={bm} t={t} />
        </div>
        <UpcomingTests tests={tests} batches={bm} t={t} />
      </div>
      {can(viewer, "ranks.view") && <ClassToppers tops={tops} t={t} />}
    </>
  );
}

/** Faculty: own batches, attendance to mark, today's classes, tests. */
export async function FacultyHome({ viewer }: { viewer: StaffViewer }) {
  const { t } = await getT();
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
  const [low, duty] = await Promise.all([lowAttendance(today, students), dutyTests(viewer.user.id, addDays(today, -7))]);
  const dutyOpen = duty.filter((x) => !x.done_at && x.date <= addDays(today, 14));
  const bm = batchMap(mine);
  const weekday = weekdayOf(today);
  const todayEntries = entries.filter((e) => e.weekday === weekday);
  const counts = new Map<string, number>();
  for (const s of students) if (s.batch_id) counts.set(s.batch_id, (counts.get(s.batch_id) ?? 0) + 1);

  return (
    <>
      {dutyOpen.length > 0 && (
        <Section title={t("academics.duty.homeTitle")}>
          <Card className="divide-y divide-line overflow-hidden">
            {dutyOpen.map((x) => (
              <Link key={x.id} href={x.date <= today ? `/tests/${x.id}/attendance` : "/timetable"} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary-soft text-primary">
                  <UserCheck size={19} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14.5px] font-bold">{x.name}</span>
                  <span className="block truncate text-[12.5px] text-muted">
                    {boardName(x.board)} {x.class} · {dayLabel(x.date)}
                    {x.start_time ? ` · ${clockLabel(x.start_time)}` : ""}
                  </span>
                </span>
                {x.date < today ? (
                  <Chip tone="danger">{t("academics.duty.pending")}</Chip>
                ) : x.date === today ? (
                  <Chip tone="warn">{t("academics.duty.markNow")}</Chip>
                ) : (
                  <Chip>{dayLabel(x.date).split(",")[0]}</Chip>
                )}
              </Link>
            ))}
          </Card>
        </Section>
      )}
      <Section title={t("admin.home.myBatches")} action={can(viewer, "attendance.mark") ? <SectionLink href="/attendance">{t("admin.home.attendance")}</SectionLink> : undefined}>
        {mine.length === 0 ? (
          <Empty>{t("admin.home.noBatches")}</Empty>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
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
                      <p className="text-[12.5px] text-muted">{t("admin.home.nStudents", { n: counts.get(b.id) ?? 0 })}</p>
                      {missedYesterday && <p className="text-[12px] font-semibold text-danger">{t("admin.home.yesterdayNotMarked")}</p>}
                    </div>
                    {marked ? <Chip tone="ok">{t("admin.home.marked")}</Chip> : meets ? <Chip tone="warn">{t("admin.home.markToday")}</Chip> : <Chip>{t("admin.home.noClass")}</Chip>}
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </Section>
      <div className="grid grid-cols-1 gap-x-6 lg:grid-cols-2">
        <TodayClasses entries={todayEntries} batches={bm} t={t} />
        <UpcomingTests tests={tests} batches={bm} title={t("admin.home.upcomingMine")} t={t} />
      </div>
      {can(viewer, "students.view") && <LowAttendanceList list={low} batches={bm} t={t} />}
    </>
  );
}
