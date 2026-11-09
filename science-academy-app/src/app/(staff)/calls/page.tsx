import Link from "next/link";
import { notFound } from "next/navigation";
import { AlertTriangle, CalendarCheck, Phone, PhoneCall, ReceiptText } from "lucide-react";
import { can, canSeeBatch, requirePermission, type StaffViewer } from "@/lib/auth";
import { callList, guardiansOf, outstandingFor, studentsById, attemptsSince, type CallListEntry } from "@/lib/fees-data";
import { callBucket, type CallBucket } from "@/lib/billing-calc";
import { CALL_OUTCOME_LABEL, daysLate } from "@/lib/fees";
import { dateLabel, dateTimeLabel, monthLabel, monthStart, rupees, todayIst } from "@/lib/format";
import { formatMobile, maskMobile } from "@/lib/ids";
import { Banner, Card, Chip, Empty, Page, PageHeader, Section, Stat } from "@/components/ui";
import { openCallTasks } from "@/lib/fee-automation";
import { CallDone } from "./CallDone";

export const metadata = { title: "Call log" };

const SECTIONS: { bucket: CallBucket; title: string }[] = [
  { bucket: "promised_due", title: "Promised for today (or earlier)" },
  { bucket: "call", title: "To call (longest overdue first)" },
  { bucket: "escalated", title: "Escalated to admin" },
  { bucket: "promised_later", title: "Promised a later date" },
];

const RELATION = { father: "Father", mother: "Mother", guardian: "Guardian", alternate: "Alternate" } as const;

export default async function CallsPage({ searchParams }: { searchParams: Promise<{ student?: string }> }) {
  const viewer = await requirePermission("fees.view");
  const { student: focusId } = await searchParams;
  const today = todayIst();
  let list = (await callList(today)).filter((e) => canSeeBatch(viewer, e.student.batch_id));

  let focusNote: string | null = null;
  if (focusId) {
    if (!/^[0-9a-f-]{36}$/i.test(focusId)) notFound();
    let entry = list.find((e) => e.studentId === focusId);
    if (!entry) {
      // Not overdue (yet): still allow calling and logging.
      const entryBuilt = await buildEntry(focusId, today, viewer);
      if (!entryBuilt) notFound();
      entry = entryBuilt;
      focusNote = entry.totalDue > 0 ? "This student's fee is not overdue yet." : "Nothing is pending for this student.";
    }
    list = [entry];
  }

  const showNumbers = can(viewer, "students.contacts");
  const totalDue = list.reduce((s, e) => s + e.totalDue, 0);
  // Call tasks made the day after a due date (fee still unpaid): on top until a call is logged.
  const tasks = focusId ? [] : await openCallTasks();
  const taskIds = new Set(tasks.map((t) => t.student_id));
  const taskItems = list.filter((e) => taskIds.has(e.studentId));
  const rest = list.filter((e) => !taskIds.has(e.studentId));
  const groups = SECTIONS.map((s) => ({ ...s, items: rest.filter((e) => callBucket(e, today) === s.bucket) })).filter((g) => g.items.length);

  return (
    <>
      <PageHeader title="Call log" subtitle="Parents to call about fees" back={focusId ? "/calls" : undefined} />
      <Page>
        {!focusId && (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="To call" value={list.filter((e) => ["call", "promised_due"].includes(callBucket(e, today))).length} />
            <Stat label="Overdue amount" value={rupees(totalDue)} tone="danger" />
            <Stat label="Call tasks today" value={taskItems.length} tone="danger" />
            <Stat label="Promised today" value={list.filter((e) => callBucket(e, today) === "promised_due").length} tone="primary" />
            <Stat label="Escalated" value={list.filter((e) => callBucket(e, today) === "escalated").length} tone="warn" />
          </div>
        )}
        {focusNote && <Banner tone="navy">{focusNote}</Banner>}
        {!showNumbers && (
          <div className="mt-3">
            <Banner tone="warn" icon={AlertTriangle}>
              Your login cannot see parents&apos; phone numbers. Admin can change this in Access control.
            </Banner>
          </div>
        )}
        <div className="mt-2 rounded-field bg-field px-3 py-2 text-xs text-muted">
          Fee reminders go to each parent privately. Never post fee messages in a batch group.
        </div>

        {list.length === 0 && (
          <div className="mt-5">
            <Empty icon={PhoneCall}>No overdue fees. Nobody to call today.</Empty>
          </div>
        )}

        {taskItems.length > 0 && (
          <Section title={`Today's call tasks · ${taskItems.length}`}>
            <p className="-mt-1 mb-2 text-xs text-muted">The fee was due and is still not paid. Logging the call closes the task.</p>
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {taskItems.map((e) => (
                <CallCard key={e.studentId} e={e} today={today} showNumbers={showNumbers} canBill={can(viewer, "bills.create")} />
              ))}
            </div>
          </Section>
        )}

        {groups.map((g) => (
          <Section key={g.bucket} title={`${g.title} · ${g.items.length}`}>
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {g.items.map((e) => (
                <CallCard key={e.studentId} e={e} today={today} showNumbers={showNumbers} canBill={can(viewer, "bills.create")} />
              ))}
            </div>
          </Section>
        ))}
      </Page>
    </>
  );
}

function CallCard({ e, today, showNumbers, canBill }: { e: CallListEntry; today: string; showNumbers: boolean; canBill: boolean }) {
  const login = e.guardians.find((g) => g.is_login_number) ?? e.guardians[0];
  const others = e.guardians.filter((g) => g !== login);
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href={`/fees/${e.studentId}`} className="font-bold text-navy hover:text-primary">
            {e.student.name}
          </Link>
          <p className="text-xs text-muted">
            {e.student.code} · Class {e.student.current_class}
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-extrabold text-danger">{rupees(e.totalDue)}</p>
          <p className="text-xs font-semibold text-muted">{e.daysLate > 0 ? `${e.daysLate} days late` : "not late yet"}</p>
        </div>
      </div>
      <p className="mt-1 text-xs text-muted">Unpaid since {monthLabel(e.oldestMonth)}</p>

      {login ? (
        <div className="mt-3 flex items-center gap-3 rounded-field bg-field px-3 py-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold">
              {login.name ?? RELATION[login.relation]} <span className="font-normal text-muted">· {RELATION[login.relation]}</span>
            </p>
            <p className="text-[15px] font-semibold tracking-wide">{showNumbers ? `+91 ${formatMobile(login.mobile)}` : maskMobile(login.mobile)}</p>
          </div>
          {showNumbers && (
            <a href={`tel:+91${login.mobile}`} className="btn btn-primary px-3" aria-label={`Call ${login.name ?? "parent"}`}>
              <Phone size={16} /> Call
            </a>
          )}
        </div>
      ) : (
        <p className="mt-3 text-sm text-danger">No phone number saved.</p>
      )}
      {others.length > 0 && (
        <div className="mt-2 space-y-1">
          {others.map((g) => (
            <div key={g.id} className="flex items-center gap-2 text-[13px]">
              <span className="flex-1 text-muted">
                {g.name ?? RELATION[g.relation]} ({RELATION[g.relation]}) · {showNumbers ? formatMobile(g.mobile) : maskMobile(g.mobile)}
              </span>
              {showNumbers && (
                <a href={`tel:+91${g.mobile}`} className="font-bold text-primary">
                  Call
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <Chip tone={e.attempts ? "navy" : "neutral"}>
          {e.attempts ? `${e.attempts} previous attempt${e.attempts === 1 ? "" : "s"}` : "Not called yet"}
        </Chip>
        {e.lastOutcome && (
          <Chip tone={e.lastOutcome === "needs_admin" || e.lastOutcome === "wrong_number" ? "danger" : "primary"}>{CALL_OUTCOME_LABEL[e.lastOutcome]}</Chip>
        )}
        {e.followUpDate && (
          <Chip tone={e.followUpDate <= today ? "warn" : "neutral"}>
            <CalendarCheck size={12} /> {dateLabel(e.followUpDate)}
          </Chip>
        )}
      </div>
      {e.lastNote && <p className="mt-1.5 text-[13px] text-muted">“{e.lastNote}”</p>}
      {e.lastCallAt && <p className="mt-0.5 text-[11.5px] text-faint">Last call {dateTimeLabel(e.lastCallAt)}</p>}

      <div className="mt-3 flex flex-wrap gap-2">
        {e.guardians.length > 0 && (
          <CallDone
            studentId={e.studentId}
            studentName={e.student.name}
            attempt={e.attempts + 1}
            today={today}
            numbers={e.guardians.map((g) => ({
              id: g.id,
              label: `${g.name ?? RELATION[g.relation]} (${RELATION[g.relation]})${showNumbers ? ` · ${formatMobile(g.mobile)}` : ""}${g.is_login_number ? " · login" : ""}`,
            }))}
          />
        )}
        {canBill && (
          <Link href={`/billing/new?student=${e.studentId}`} className="btn btn-ghost px-3 py-1.5 text-[13px]">
            <ReceiptText size={15} /> Make bill
          </Link>
        )}
      </div>
    </Card>
  );
}

/** A call card for a student who is not on the overdue list. */
async function buildEntry(studentId: string, today: string, viewer: StaffViewer): Promise<CallListEntry | null> {
  const [students, guardians, due] = await Promise.all([studentsById([studentId]), guardiansOf([studentId]), outstandingFor(studentId, today)]);
  const student = students.get(studentId);
  if (!student || !canSeeBatch(viewer, student.batch_id)) return null;
  const oldest = due.months[0] ?? monthStart(today);
  return {
    studentId,
    oldestMonth: oldest,
    totalDue: due.total,
    daysLate: due.months[0] ? daysLate(oldest, today, due.dues[0]) : 0,
    attempts: await attemptsSince(studentId, oldest),
    lastOutcome: null,
    followUpDate: null,
    lastCallAt: null,
    lastNote: null,
    student,
    guardians: guardians.get(studentId) ?? [],
  };
}
