import "server-only";
import { adminClient } from "./supabase/admin";
import { activeUsersWithRole, notify, parentUserOf, type NewNotification } from "./notify";
import { addDays, dateLabel, rupees, todayIst } from "./format";
import { sendFeeTemplate } from "./whatsapp";
import { all, localize, type TFn } from "./i18n";

type Due = { id: string; student_id: string; month: string; amount: number; paid: number; due_date: string; label: string | null };
type StudentLite = { id: string; name: string; code: string | null; status: string };

/** Fee rows with money left whose due date is `date`, for active students. */
async function dueOn(date: string): Promise<{ row: Due; student: StudentLite }[]> {
  const db = adminClient();
  const { data } = await db.from("fees_ledger").select("*").eq("due_date", date);
  const rows = ((data ?? []) as Due[]).filter((r) => Number(r.amount) - Number(r.paid) > 0);
  if (!rows.length) return [];
  const { data: st } = await db.from("students").select("id, name, code, status").in("id", [...new Set(rows.map((r) => r.student_id))]);
  const byId = new Map(((st ?? []) as StudentLite[]).map((s) => [s.id, s]));
  return rows.flatMap((row) => {
    const student = byId.get(row.student_id);
    return student && student.status === "active" ? [{ row, student }] : [];
  });
}

const balance = (r: Due) => Math.round((Number(r.amount) - Number(r.paid)) * 100) / 100;

function names(list: { student: StudentLite }[], t: TFn): string {
  const first = list.slice(0, 4).map((x) => x.student.name).join(", ");
  return list.length > 4 ? t("core.rem.andMore", { names: first, n: list.length - 4 }) : first;
}

/**
 * Runs once a day:
 *  1. Due tomorrow → each parent gets a WhatsApp message (when WhatsApp is set
 *     up) and an in-app reminder.
 *  2. Due today → Reception is told who is due today, to call tomorrow if unpaid.
 *  3. Due yesterday and still unpaid → a call task per student for Reception today.
 * Every step is safe to run again on the same day.
 */
export async function runFeeAutomation(now: Date = new Date()): Promise<Record<string, number>> {
  const today = todayIst(now);
  const tomorrow = addDays(today, 1);
  const yesterday = addDays(today, -1);
  const db = adminClient();
  const remindedRows: { student_id: string; month: string }[] = [];
  const counts = { whatsapp_sent: 0, whatsapp_failed: 0, whatsapp_skipped: 0, parent_reminders: 0, due_today: 0, call_tasks: 0 };
  const items: NewNotification[] = [];

  // 1. One day before: parents.
  for (const { row, student } of await dueOn(tomorrow)) {
    const parent = await parentUserOf(student.id);
    if (!parent) continue;
    const amount = rupees(balance(row));
    const when = dateLabel(row.due_date);
    items.push({
      userId: parent.id,
      kind: "fee_reminder",
      title: all("core.rem.feeDueTomorrowTitle", { amount }),
      body: localize((t) => t("core.rem.feeDueTomorrowBody", { student: student.name, what: row.label ?? t("core.rem.feeWord"), amount, date: when })),
      link: "/parent/fees",
      dedupeKey: `fee-due-tomorrow-${row.id}`,
    });
    counts.parent_reminders++;
    remindedRows.push({ student_id: student.id, month: row.month });
    // WhatsApp once per fee row (a unique index stops a second "sent").
    const { data: already } = await db.from("whatsapp_messages").select("id").eq("ledger_id", row.id).eq("kind", "fee_due_tomorrow").eq("status", "sent").maybeSingle();
    if (already) continue;
    const res = await sendFeeTemplate(parent.mobile, [student.name, amount.replace("₹", "Rs. "), when]);
    await db.from("whatsapp_messages").insert({
      ledger_id: row.id,
      student_id: student.id,
      kind: "fee_due_tomorrow",
      to_mobile: parent.mobile,
      status: res.ok ? "sent" : res.skipped ? "skipped" : "failed",
      error: res.ok ? null : res.error,
      provider_id: res.ok ? res.id : null,
    });
    if (res.ok) counts.whatsapp_sent++;
    else if (res.skipped) counts.whatsapp_skipped++;
    else counts.whatsapp_failed++;
  }
  if (remindedRows.length) {
    // Part of the reminder chain on the dashboard (once a day per student).
    const { data: done } = await db
      .from("fee_reminders")
      .select("student_id")
      .eq("stage", "reminded")
      .gte("created_at", `${today}T00:00:00+05:30`)
      .in("student_id", remindedRows.map((r) => r.student_id));
    const skip = new Set(((done ?? []) as { student_id: string }[]).map((d) => d.student_id));
    const fresh = remindedRows.filter((r) => !skip.has(r.student_id)).map((r) => ({ ...r, stage: "reminded" }));
    if (fresh.length) await db.from("fee_reminders").insert(fresh);
  }

  const reception = await activeUsersWithRole(["reception"]);

  // 2. On the due date: Reception knows who to call tomorrow if they do not pay.
  const dueToday = await dueOn(today);
  if (dueToday.length) {
    counts.due_today = dueToday.length;
    const total = dueToday.reduce((s, x) => s + balance(x.row), 0);
    for (const u of reception) {
      items.push({
        userId: u.id,
        kind: "fees_due_today",
        title: dueToday.length === 1 ? all("core.rem.dueTodayOne", { amount: rupees(total) }) : all("core.rem.dueToday", { n: dueToday.length, amount: rupees(total) }),
        body: localize((t) => t("core.rem.dueTodayBody", { names: names(dueToday, t) })),
        link: "/fees",
        dedupeKey: `fees-due-today-${today}`,
      });
    }
  }

  // 3. The day after: a call task per unpaid fee row.
  const late = await dueOn(yesterday);
  if (late.length) {
    const { data: made } = await db
      .from("call_tasks")
      .upsert(
        late.map(({ row, student }) => ({ student_id: student.id, ledger_id: row.id, due_date: row.due_date, task_date: today })),
        { onConflict: "ledger_id", ignoreDuplicates: true },
      )
      .select("id");
    counts.call_tasks = made?.length ?? 0;
    for (const u of reception) {
      items.push({
        userId: u.id,
        kind: "call_tasks",
        title: late.length === 1 ? all("core.rem.callTasksOne") : all("core.rem.callTasks", { n: late.length }),
        body: localize((t) => t("core.rem.callTasksBody", { names: names(late, t) })),
        link: "/calls",
        dedupeKey: `call-tasks-${today}`,
      });
    }
  }

  await notify(items);
  return counts;
}

export type CallTask = { id: string; student_id: string; due_date: string; task_date: string };

/** Open call tasks (oldest first), for the top of the call log. */
export async function openCallTasks(): Promise<CallTask[]> {
  const { data, error } = await adminClient().from("call_tasks").select("id, student_id, due_date, task_date").eq("status", "open").order("task_date");
  if (error) return []; // table not made yet (migration not run)
  return (data ?? []) as CallTask[];
}
