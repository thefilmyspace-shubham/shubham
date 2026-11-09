import "server-only";
import { all, localize } from "./i18n";
import { adminClient } from "./supabase/admin";
import { addDays, todayIst, weekdayOf } from "./format";
import { toIst } from "./ids";
import { allBatches, batchLabel } from "./batches";
import { activeUsersWithRole, notify, type NewNotification } from "./notify";
import { activeStudents, attendanceOn, callsDue, escalations, feeOverview, latestCalls, timetableFor, batchMeets } from "./dashboard";
import { rupees } from "./format";

/**
 * Daily in-app reminders (the bell). Safe to run many times a day: every
 * notification has a dedupe key, so each person gets each reminder once.
 *  - Reception: calls due today (overdue fees, promised dates due today)
 *  - Faculty: attendance not marked for their batches (yesterday; today too after 11 AM)
 *  - Admin: escalations ("Needs admin" calls)
 */
export async function runDailyReminders(now: Date = new Date()): Promise<Record<string, number>> {
  const today = todayIst(now);
  const hour = toIst(now).getUTCHours();
  const counts: Record<string, number> = { calls_due: 0, attendance_missing: 0, escalations: 0 };
  const items: NewNotification[] = [];

  // Fees: Reception and Admin.
  const students = await activeStudents();
  const fees = await feeOverview(today, students);
  const calls = await latestCalls();
  const due = callsDue(fees, calls, today);
  if (due.length) {
    const promised = due.filter((d) => d.reason !== "overdue").length;
    const total = due.reduce((s, d) => s + d.owing.overdue, 0);
    const reception = await activeUsersWithRole(["reception"]);
    for (const u of reception) {
      items.push({
        userId: u.id,
        kind: "calls_due",
        title: due.length === 1 ? all("core.rem.callsDueOne") : all("core.rem.callsDue", { n: due.length }),
        body: promised ? all("core.rem.overduePromised", { amount: rupees(total), n: promised }) : all("core.rem.overdue", { amount: rupees(total) }),
        link: "/calls",
        dedupeKey: `calls-due-${today}`,
      });
    }
    counts.calls_due = reception.length;
  }

  const esc = escalations(fees, calls);
  if (esc.length) {
    const admins = await activeUsersWithRole(["admin"]);
    const names = new Map(students.map((s) => [s.id, s]));
    for (const c of esc) {
      const s = names.get(c.student_id);
      for (const a of admins) {
        items.push({
          userId: a.id,
          kind: "escalation",
          title: localize((t) => t("core.rem.needsAdmin", { name: `${s?.name ?? t("core.rem.aStudent")}${s?.code ? ` (${s.code})` : ""}` })),
          body: localize((t) => `${t("core.rem.pending", { amount: rupees(fees.owing.get(c.student_id)?.balance ?? 0) })}${c.note ? ` · ${c.note.slice(0, 100)}` : ""}`),
          link: `/calls?student=${c.student_id}`,
          dedupeKey: `escalation-${c.id}`,
        });
        counts.escalations++;
      }
    }
  }

  // Attendance: each faculty member's batches.
  const db = adminClient();
  const [{ data: links }, batches, faculty] = await Promise.all([
    db.from("faculty_batches").select("user_id, batch_id"),
    allBatches(),
    activeUsersWithRole(["faculty"]),
  ]);
  const active = new Map(batches.map((b) => [b.id, b]));
  const entries = await timetableFor(null);
  const days = hour >= 11 ? [addDays(today, -1), today] : [addDays(today, -1)];
  const facultyIds = new Set(faculty.map((f) => f.id));
  for (const date of days) {
    const att = await attendanceOn(date);
    const weekday = weekdayOf(date);
    for (const l of (links ?? []) as { user_id: string; batch_id: string }[]) {
      const b = active.get(l.batch_id);
      if (!b || !facultyIds.has(l.user_id)) continue;
      if (!batchMeets(b.id, weekday, entries) || att.markedBatches.has(b.id)) continue;
      // Only remind for a batch that has students.
      if (!students.some((s) => s.batch_id === b.id)) continue;
      items.push({
        userId: l.user_id,
        kind: "attendance_missing",
        title: all("core.rem.attNotMarked", { batch: batchLabel(b) }),
        body: date === today ? all("core.today") : all("core.yesterday"),
        link: `/attendance/${b.id}?date=${date}`,
        dedupeKey: `att-${b.id}-${date}`,
      });
      counts.attendance_missing++;
    }
  }

  await notify(items);
  return counts;
}
