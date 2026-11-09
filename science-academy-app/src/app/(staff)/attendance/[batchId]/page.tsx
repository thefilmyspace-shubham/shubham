import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft, ChevronRight, Info, Lock } from "lucide-react";
import { can, canSeeBatch, requireStaff } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { batchLabel } from "@/lib/batches";
import { addDays, dayLabel, todayIst } from "@/lib/format";
import { activeStudentsOfBatches } from "@/lib/academics";
import { attendanceOn, canChangeRow, isIsoDate, isLocked } from "@/lib/attendance";
import type { Batch } from "@/lib/types";
import { Banner, Empty, Page, PageHeader } from "@/components/ui";
import { AttendanceSheet, type SheetRow } from "./AttendanceSheet";

export const metadata = { title: "Mark attendance" };

export default async function BatchAttendancePage({
  params,
  searchParams,
}: {
  params: Promise<{ batchId: string }>;
  searchParams: Promise<{ date?: string }>;
}) {
  const viewer = await requireStaff();
  const { batchId } = await params;
  const { date: dateParam } = await searchParams;
  if (!can(viewer, "attendance.mark") && !can(viewer, "students.view")) notFound();
  if (!/^[0-9a-f-]{36}$/i.test(batchId) || !canSeeBatch(viewer, batchId)) notFound();

  const today = todayIst();
  const date = isIsoDate(dateParam) && dateParam <= today ? dateParam : today;
  const { data: batch } = await adminClient().from("batches").select("*").eq("id", batchId).maybeSingle<Batch>();
  if (!batch) notFound();

  const students = await activeStudentsOfBatches([batch.id]);
  const [rows, { data: noteRow }] = await Promise.all([
    attendanceOn(
      students.map((s) => s.id),
      date,
    ),
    adminClient().from("attendance_notes").select("note").eq("batch_id", batch.id).eq("date", date).maybeSingle<{ note: string }>(),
  ]);
  const byStudent = new Map(rows.map((r) => [r.student_id, r]));
  const canMark = can(viewer, "attendance.mark");
  const canCorrect = can(viewer, "attendance.correct");
  const now = new Date();

  const sheet: SheetRow[] = students.map((s) => {
    const row = byStudent.get(s.id) ?? null;
    return {
      id: s.id,
      name: s.name,
      code: s.code,
      status: row?.status ?? null,
      locked: row ? isLocked(row.locked_at, now) : false,
      editable: canChangeRow(row, canMark, canCorrect, now),
    };
  });
  const lockedCount = sheet.filter((r) => r.locked).length;
  const correcting = lockedCount > 0 && canCorrect;
  const readOnly = !sheet.some((r) => r.editable);

  const prev = addDays(date, -1);
  const next = addDays(date, 1);

  return (
    <>
      <PageHeader title={batchLabel(batch)} subtitle={`${dayLabel(date)}${date === today ? " · Today" : ""} · ${students.length} students`} back="/attendance" />
      <Page>
        <div className="mb-3 flex items-center gap-2">
          <Link href={`/attendance/${batch.id}?date=${prev}`} className="btn btn-ghost px-2.5" aria-label="Previous day">
            <ChevronLeft size={18} />
          </Link>
          <form className="flex flex-1 items-center gap-2">
            <input type="date" name="date" defaultValue={date} max={today} className="field py-2" aria-label="Date" />
            <button className="btn btn-soft">Go</button>
          </form>
          {date < today ? (
            <Link href={`/attendance/${batch.id}?date=${next}`} className="btn btn-ghost px-2.5" aria-label="Next day">
              <ChevronRight size={18} />
            </Link>
          ) : (
            <span className="btn btn-ghost px-2.5 opacity-40" aria-hidden>
              <ChevronRight size={18} />
            </span>
          )}
        </div>

        <div className="mb-3 space-y-2">
          {lockedCount > 0 && (
            <Banner tone={canCorrect ? "warn" : "neutral"} icon={Lock}>
              {canCorrect
                ? "This day is locked (saved more than 24 hours ago). Any change you make is a correction and is written to the activity log."
                : "This day is locked (saved more than 24 hours ago). Only Admin or Management can correct it."}
            </Banner>
          )}
          {readOnly && !lockedCount && (
            <Banner tone="neutral" icon={Info}>
              View only. Faculty mark attendance for their own batches.
            </Banner>
          )}
        </div>

        {students.length === 0 ? (
          <Empty>No active students in this batch.</Empty>
        ) : (
          <AttendanceSheet
            key={date}
            batchId={batch.id}
            date={date}
            rows={sheet}
            note={noteRow?.note ?? ""}
            canEditNote={canMark || canCorrect}
            correcting={correcting}
          />
        )}
      </Page>
    </>
  );
}
