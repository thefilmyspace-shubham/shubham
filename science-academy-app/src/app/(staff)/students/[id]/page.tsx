import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { CheckCircle2, Eye, FileText, IndianRupee, NotebookPen, Pencil, Phone, PhoneCall, ReceiptText, RefreshCw } from "lucide-react";
import { can, canSeeStudent, requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { batchShort } from "@/lib/batches";
import { boardName, formatMobile, sessionLabel } from "@/lib/ids";
import { dateLabel, monthLabel, monthShort, monthStart, rupees, todayIst } from "@/lib/format";
import { balanceOf, dueDate, feeStatus, FEE_STATUS_LABEL, type FeeStatus } from "@/lib/fees";
import { ROLE_LABEL } from "@/lib/permissions";
import { AI_CHECK_LABEL, AI_CHECK_TONE } from "@/lib/ai/marksheet-compare";
import { earlierIds, facultyNotes, getStudent, RELATION_LABEL, studentDetails, studentProfileNumbers } from "@/lib/students";
import type { Batch, LedgerRow } from "@/lib/types";
import { BarChart } from "@/components/BarChart";
import { Banner, Card, Chip, Empty, Page, PageHeader, Section, Stat } from "@/components/ui";
import { addFacultyNote, recheckMarksheet } from "../actions";

export const metadata = { title: "Student profile" };

const FEE_TONE: Record<FeeStatus, "ok" | "warn" | "primary" | "danger"> = { paid: "ok", partial: "warn", pending: "primary", overdue: "danger" };

export default async function StudentProfile({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ registered?: string; saved?: string }>;
}) {
  const viewer = await requirePermission("students.view");
  const { id } = await params;
  const sp = await searchParams;
  const student = await getStudent(id);
  if (!student || !canSeeStudent(viewer, student)) notFound();
  if (student.status === "draft") {
    if (can(viewer, "students.edit")) redirect(`/students/${student.id}/edit`);
    notFound();
  }

  const seeContacts = can(viewer, "students.contacts");
  const seeMarksheets = can(viewer, "students.marksheets");
  const seeFees = can(viewer, "fees.view");
  const canEdit = can(viewer, "students.edit");
  const canNote = ["faculty", "management", "admin"].includes(viewer.user.role);
  const today = todayIst();
  const month = monthStart(today);

  const db = adminClient();
  const [details, numbers, notes, batchRes, ledgerRes] = await Promise.all([
    studentDetails(student.id),
    studentProfileNumbers(student, today),
    facultyNotes(student.id),
    student.batch_id ? db.from("batches").select("*").eq("id", student.batch_id).maybeSingle<Batch>() : Promise.resolve({ data: null }),
    seeFees ? db.from("fees_ledger").select("*").eq("student_id", student.id).eq("month", month).maybeSingle<LedgerRow>() : Promise.resolve({ data: null }),
  ]);
  const batch = batchRes.data as Batch | null;
  const earlier = earlierIds(details.history, student.code);

  const hidden: string[] = [];
  if (!seeContacts) hidden.push("contact numbers");
  if (!seeFees) hidden.push("fees");
  if (!seeMarksheets) hidden.push("marksheets");
  const list = hidden.length > 1 ? `${hidden.slice(0, -1).join(", ")} and ${hidden[hidden.length - 1]}` : hidden[0];
  const banner = hidden.length
    ? `${ROLE_LABEL[viewer.user.role]} see this page without ${list}.`
    : "You see everything on this page, including contact numbers and fees.";

  const { thisMonth, byMonth } = numbers.attendance;
  const ledger = ledgerRes.data as LedgerRow | null;
  const feeAmount = ledger ? Number(ledger.amount) : Number(student.monthly_fee);
  const feePaid = ledger ? Number(ledger.paid) : 0;
  const status = feeStatus(feeAmount, feePaid, month, today);

  return (
    <>
      <PageHeader
        title={student.name}
        subtitle={student.code}
        back="/students"
        right={
          canEdit ? (
            <Link href={`/students/${student.id}/edit`} className="btn btn-ghost">
              <Pencil size={15} /> <span className="hidden sm:inline">Edit</span>
            </Link>
          ) : undefined
        }
      />
      <Page wide>
        <div className="space-y-3">
          {sp.registered && (
            <Banner tone="ok" icon={CheckCircle2}>
              Registered. Student ID <b>{student.code}</b>. The parent can log in with the login number.
            </Banner>
          )}
          {sp.saved && (
            <Banner tone="ok" icon={CheckCircle2}>
              Changes saved.
            </Banner>
          )}
          <Banner tone="navy" icon={Eye}>
            {banner}
          </Banner>
        </div>

        <Card className="mt-3 overflow-hidden">
          <div className="bg-navy px-4 py-4 text-white lg:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-2xl font-extrabold tracking-tight">{student.code}</span>
              {student.status !== "active" && <Chip tone="warn">{student.status === "left" ? "Left" : "Passed out"}</Chip>}
            </div>
            {earlier.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-white/70">Earlier ID</span>
                {earlier.map((c) => (
                  <span key={c} className="rounded-full bg-white/15 px-2 py-0.5 font-mono text-[11.5px] font-bold">
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-4 text-sm sm:grid-cols-4 lg:px-6">
            <div>
              <dt className="text-xs text-muted">Class</dt>
              <dd className="font-bold">Class {student.current_class}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Board</dt>
              <dd className="font-bold">{boardName(student.board)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Batch</dt>
              <dd className="font-bold">{batch ? batchShort(batch) : "Not set"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Admission session</dt>
              <dd className="font-bold">{student.admission_session !== null ? sessionLabel(student.admission_session) : "—"}</dd>
            </div>
            {student.school && (
              <div className="col-span-2 sm:col-span-4">
                <dt className="text-xs text-muted">School</dt>
                <dd className="font-bold">{student.school}</dd>
              </div>
            )}
          </dl>
        </Card>

        <div className="mt-3 grid grid-cols-3 gap-3">
          <Stat
            label="Attendance this month"
            value={thisMonth.total ? `${thisMonth.pct}%` : "—"}
            hint={thisMonth.total ? `${thisMonth.present} of ${thisMonth.total} days` : "Not marked yet"}
            tone={thisMonth.total && thisMonth.pct < 75 ? "danger" : "ok"}
          />
          <Stat label="Test average" value={numbers.average !== null ? `${numbers.average}%` : "—"} hint={`${numbers.results.length} tests`} tone="primary" />
          <Stat
            label="Rank in class"
            value={numbers.rank ? `#${numbers.rank.rank}` : "—"}
            hint={numbers.rank ? `of ${numbers.rank.of} in Class ${student.current_class}` : "No scores yet"}
          />
        </div>

        <div className="grid grid-cols-1 gap-x-4 lg:grid-cols-[1fr_360px]">
          <div>
            <Section title="Recent tests">
              {numbers.results.length ? (
                <Card className="divide-y divide-line">
                  {numbers.results.slice(0, 8).map((r) => (
                    <div key={r.test_id} className="flex items-center gap-3 px-4 py-2.5">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[14px] font-semibold">{r.name}</p>
                        <p className="text-xs text-muted">
                          {dateLabel(r.date)}
                          {r.subject ? ` · ${r.subject}` : ""}
                        </p>
                      </div>
                      <Chip tone={r.tag === "School" ? "violet" : "primary"}>{r.tag}</Chip>
                      <div className="w-20 text-right">
                        {r.absent ? (
                          <span className="text-sm font-bold text-danger">Absent</span>
                        ) : (
                          <>
                            <p className="text-sm font-bold">
                              {r.score ?? "—"}
                              {r.max_marks ? <span className="text-muted">/{r.max_marks}</span> : null}
                            </p>
                            {r.pct !== null && <p className="text-xs text-muted">{r.pct}%</p>}
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </Card>
              ) : (
                <Empty>No test marks yet.</Empty>
              )}
            </Section>

            <Section title="Attendance, last six months">
              <Card className="p-4">
                <BarChart
                  data={byMonth.map((m) => ({ label: monthShort(m.month), value: m.total ? m.pct : null }))}
                  max={100}
                  format={(v) => `${v}%`}
                  color="var(--color-green)"
                />
              </Card>
            </Section>

            <Section title="Faculty note">
              <Card className="divide-y divide-line">
                {notes.length ? (
                  notes.map((n) => (
                    <div key={n.id} className="px-4 py-3">
                      <p className="text-[14px] whitespace-pre-wrap">{n.note}</p>
                      <p className="mt-1 text-xs text-muted">
                        {n.author?.staff_id ?? ""} {n.author?.name ?? ""} · {dateLabel(n.created_at.slice(0, 10))}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="px-4 py-3 text-sm text-muted">No notes yet.</p>
                )}
                {canNote && (
                  <form action={addFacultyNote} className="flex flex-col gap-2 p-3 sm:flex-row">
                    <input type="hidden" name="student_id" value={student.id} />
                    <textarea name="note" rows={2} required maxLength={1000} className="field flex-1 resize-none" placeholder="Add a note about this student" />
                    <button className="btn btn-soft self-end">
                      <NotebookPen size={15} /> Add note
                    </button>
                  </form>
                )}
              </Card>
            </Section>
          </div>

          <div>
            {seeContacts && (
              <Section title="Contact">
                <Card className="divide-y divide-line">
                  {details.guardians.map((g) => (
                    <div key={g.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[14px] font-semibold">
                          {g.name ?? RELATION_LABEL[g.relation]} <span className="font-normal text-muted">· {RELATION_LABEL[g.relation]}</span>
                        </p>
                        <p className="font-mono text-[13px]">+91 {formatMobile(g.mobile)}</p>
                        <div className="mt-1">{g.is_login_number ? <Chip tone="ok">Login number</Chip> : <Chip>Contact only</Chip>}</div>
                      </div>
                      <a href={`tel:+91${g.mobile}`} className="grid h-10 w-10 place-items-center rounded-full bg-green-soft text-green" aria-label={`Call ${g.name ?? g.relation}`}>
                        <Phone size={18} />
                      </a>
                    </div>
                  ))}
                  {!details.guardians.length && <p className="px-4 py-3 text-sm text-muted">No numbers entered.</p>}
                  {student.email && <p className="px-4 py-3 text-sm">Email: {student.email}</p>}
                </Card>
              </Section>
            )}

            {seeFees && (
              <Section title="Fees">
                <Card className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs text-muted">{monthLabel(month)} · due {dateLabel(dueDate(month))}</p>
                      <p className="mt-1 text-xl font-extrabold">{rupees(feeAmount)}</p>
                      <p className="text-xs text-muted">
                        Paid {rupees(feePaid)} · Balance {rupees(balanceOf({ amount: feeAmount, paid: feePaid }))}
                      </p>
                    </div>
                    <Chip tone={FEE_TONE[status]}>
                      <IndianRupee size={11} /> {FEE_STATUS_LABEL[status]}
                    </Chip>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {can(viewer, "bills.create") && (
                      <Link href={`/billing/new?student=${student.id}`} className="btn btn-primary">
                        <ReceiptText size={15} /> Make bill
                      </Link>
                    )}
                    <Link href={`/calls?student=${student.id}`} className="btn btn-soft">
                      <PhoneCall size={15} /> Call parent
                    </Link>
                  </div>
                  <Link href={`/fees/${student.id}`} className="mt-2 block text-center text-xs font-bold text-primary">
                    Fee ledger and reminders
                  </Link>
                </Card>
              </Section>
            )}

            {seeMarksheets && (
              <Section title="Documents">
                <Card className="divide-y divide-line">
                  {details.marksheets.length ? (
                    details.marksheets.map((m) => (
                      <div key={m.id} className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FileText size={16} className="shrink-0 text-muted" />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-[14px] font-semibold">Marksheet {m.year_label}</p>
                            <p className="text-xs text-muted">Typed: {m.typed_percentage !== null ? `${Number(m.typed_percentage)}%` : "—"}</p>
                          </div>
                          <Chip tone={AI_CHECK_TONE[m.ai_check_result]}>{AI_CHECK_LABEL[m.ai_check_result]}</Chip>
                        </div>
                        {m.ai_note && <p className="mt-1 pl-6 text-xs text-muted">{m.ai_note}</p>}
                        <div className="mt-2 flex gap-3 pl-6">
                          {m.file_path && (
                            <a href={`/api/marksheets/${m.id}`} target="_blank" rel="noreferrer" className="text-xs font-bold text-primary">
                              Open file
                            </a>
                          )}
                          {canEdit && m.file_path && m.ai_check_result !== "matched" && (
                            <form action={recheckMarksheet}>
                              <input type="hidden" name="marksheet_id" value={m.id} />
                              <button className="flex items-center gap-1 text-xs font-bold text-primary">
                                <RefreshCw size={12} /> Check again
                              </button>
                            </form>
                          )}
                          {canEdit && (
                            <Link href={`/students/${student.id}/edit`} className="text-xs font-bold text-primary">
                              Upload better photo
                            </Link>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="px-4 py-3 text-sm text-muted">No marksheets uploaded.</p>
                  )}
                  {details.consent && (
                    <p className="px-4 py-3 text-xs text-muted">
                      Consent given by {details.consent.given_by} on {dateLabel(details.consent.given_at.slice(0, 10))}
                    </p>
                  )}
                </Card>
              </Section>
            )}
          </div>
        </div>
      </Page>
    </>
  );
}
