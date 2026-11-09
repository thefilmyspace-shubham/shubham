import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { CheckCircle2, Eye, FileText, IndianRupee, NotebookPen, Pencil, Phone, PhoneCall, ReceiptText, RefreshCw } from "lucide-react";
import { can, canSeeStudent, requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { batchShort } from "@/lib/batches";
import { boardName, formatMobile, sessionLabel } from "@/lib/ids";
import { dateLabel, monthLabel, monthShort, monthStart, rupees, todayIst } from "@/lib/format";
import { balanceOf, dueDate, feeStatus, rowDue, type FeePlan, type FeeStatus } from "@/lib/fees";
import { getT } from "@/lib/i18n/server";
import { AI_CHECK_TONE } from "@/lib/ai/marksheet-compare";
import { earlierIds, facultyNotes, getStudent, studentDetails, studentProfileNumbers } from "@/lib/students";
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
  const { t } = await getT();
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
    seeFees ? db.from("fees_ledger").select("*").eq("student_id", student.id).order("month") : Promise.resolve({ data: null }),
  ]);
  const batch = batchRes.data as Batch | null;
  const earlier = earlierIds(details.history, student.code);

  const hidden: string[] = [];
  if (!seeContacts) hidden.push(t("students.prof.hideContacts"));
  if (!seeFees) hidden.push(t("students.prof.hideFees"));
  if (!seeMarksheets) hidden.push(t("students.prof.hideMarksheets"));
  const list = hidden.length > 1 ? `${hidden.slice(0, -1).join(", ")} ${t("students.prof.and")} ${hidden[hidden.length - 1]}` : hidden[0];
  const banner = hidden.length
    ? t("students.prof.bannerHidden", { role: t(`core.role.${viewer.user.role}`), list })
    : t("students.prof.bannerAll");

  const { thisMonth, byMonth } = numbers.attendance;
  // Monthly plan: this month's row. Other plans: the next payment still open.
  const plan: FeePlan = (student.fee_plan as FeePlan | undefined) ?? "monthly";
  const rows = ((ledgerRes.data ?? []) as LedgerRow[]).map((r) => ({ ...r, amount: Number(r.amount), paid: Number(r.paid) }));
  const open = rows.filter((r) => balanceOf(r) > 0).sort((a, b) => rowDue(a).localeCompare(rowDue(b)));
  const ledger =
    plan === "monthly" ? (rows.find((r) => r.month === month) ?? null) : (open.find((r) => r.month >= month) ?? open[0] ?? rows[rows.length - 1] ?? null);
  const feeMonth = ledger?.month ?? month;
  const feeAmount = ledger ? Number(ledger.amount) : Number(student.monthly_fee);
  const feePaid = ledger ? Number(ledger.paid) : 0;
  const feeDue = ledger ? rowDue(ledger) : dueDate(month, student.fee_due_day ?? 5);
  const status = feeStatus(feeAmount, feePaid, feeMonth, today, feeDue);

  return (
    <>
      <PageHeader
        title={student.name}
        subtitle={student.code}
        back="/students"
        right={
          canEdit ? (
            <Link href={`/students/${student.id}/edit`} className="btn btn-ghost">
              <Pencil size={15} /> <span className="hidden sm:inline">{t("core.edit")}</span>
            </Link>
          ) : undefined
        }
      />
      <Page wide>
        <div className="space-y-3">
          {sp.registered && (
            <Banner tone="ok" icon={CheckCircle2}>
              {t("students.prof.registered", { code: student.code ?? "" })}
            </Banner>
          )}
          {sp.saved && (
            <Banner tone="ok" icon={CheckCircle2}>
              {t("students.prof.saved")}
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
              {student.status !== "active" && <Chip tone="warn">{student.status === "left" ? t("students.left") : t("students.passedOut")}</Chip>}
            </div>
            {earlier.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-white/70">{t("students.prof.earlierId")}</span>
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
              <dt className="text-xs text-muted">{t("students.class")}</dt>
              <dd className="font-bold">{t("students.classN", { n: student.current_class })}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">{t("students.board")}</dt>
              <dd className="font-bold">{boardName(student.board)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">{t("students.batch")}</dt>
              <dd className="font-bold">{batch ? batchShort(batch) : t("students.prof.notSet")}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">{t("students.prof.admission")}</dt>
              <dd className="font-bold">{student.admission_session !== null ? sessionLabel(student.admission_session) : "—"}</dd>
            </div>
            {student.school && (
              <div className="col-span-2 sm:col-span-4">
                <dt className="text-xs text-muted">{t("students.prof.school")}</dt>
                <dd className="font-bold">{student.school}</dd>
              </div>
            )}
          </dl>
        </Card>

        <div className="mt-3 grid grid-cols-3 gap-3">
          <Stat
            label={t("students.prof.attThisMonth")}
            value={thisMonth.total ? `${thisMonth.pct}%` : "—"}
            hint={thisMonth.total ? t("students.prof.daysOf", { p: thisMonth.present, t: thisMonth.total }) : t("students.prof.notMarked")}
            tone={thisMonth.total && thisMonth.pct < 75 ? "danger" : "ok"}
          />
          <Stat label={t("students.prof.testAvg")} value={numbers.average !== null ? `${numbers.average}%` : "—"} hint={t("students.prof.nTests", { n: numbers.results.length })} tone="primary" />
          <Stat
            label={t("students.prof.rank")}
            value={numbers.rank ? `#${numbers.rank.rank}` : "—"}
            hint={numbers.rank ? t("students.prof.rankOf", { n: numbers.rank.of, c: student.current_class }) : t("students.prof.noScores")}
          />
        </div>

        <div className="grid grid-cols-1 gap-x-4 lg:grid-cols-[1fr_360px]">
          <div>
            <Section title={t("students.prof.recentTests")}>
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
                          <span className="text-sm font-bold text-danger">{t("students.prof.absent")}</span>
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
                <Empty>{t("students.prof.noMarks")}</Empty>
              )}
            </Section>

            <Section title={t("students.prof.att6")}>
              <Card className="p-4">
                <BarChart
                  data={byMonth.map((m) => ({ label: monthShort(m.month), value: m.total ? m.pct : null }))}
                  max={100}
                  format={(v) => `${v}%`}
                  color="var(--color-green)"
                />
              </Card>
            </Section>

            <Section title={t("students.prof.facultyNote")}>
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
                  <p className="px-4 py-3 text-sm text-muted">{t("students.prof.noNotes")}</p>
                )}
                {canNote && (
                  <form action={addFacultyNote} className="flex flex-col gap-2 p-3 sm:flex-row">
                    <input type="hidden" name="student_id" value={student.id} />
                    <textarea name="note" rows={2} required maxLength={1000} className="field flex-1 resize-none" placeholder={t("students.prof.notePh")} />
                    <button className="btn btn-soft self-end">
                      <NotebookPen size={15} /> {t("students.prof.addNote")}
                    </button>
                  </form>
                )}
              </Card>
            </Section>
          </div>

          <div>
            {seeContacts && (
              <Section title={t("students.prof.contact")}>
                <Card className="divide-y divide-line">
                  {details.guardians.map((g) => (
                    <div key={g.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[14px] font-semibold">
                          {g.name ?? t(`students.rel.${g.relation}`)} <span className="font-normal text-muted">· {t(`students.rel.${g.relation}`)}</span>
                        </p>
                        <p className="font-mono text-[13px]">+91 {formatMobile(g.mobile)}</p>
                        <div className="mt-1">{g.is_login_number ? <Chip tone="ok">{t("students.prof.loginNumber")}</Chip> : <Chip>{t("students.prof.contactOnly")}</Chip>}</div>
                      </div>
                      <a href={`tel:+91${g.mobile}`} className="grid h-10 w-10 place-items-center rounded-full bg-green-soft text-green" aria-label={t("students.prof.call", { who: g.name ?? t(`students.rel.${g.relation}`) })}>
                        <Phone size={18} />
                      </a>
                    </div>
                  ))}
                  {!details.guardians.length && <p className="px-4 py-3 text-sm text-muted">{t("students.prof.noNumbers")}</p>}
                  {student.email && <p className="px-4 py-3 text-sm">{t("students.prof.email", { email: student.email })}</p>}
                </Card>
              </Section>
            )}

            {seeFees && (
              <Section title={t("students.prof.fees")}>
                <Card className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs text-muted">
                        {plan === "monthly" ? monthLabel(feeMonth) : `${t(`fees.plan.${plan}`)}${ledger?.label ? ` · ${ledger.label}` : ""}`} ·{" "}
                        {t("students.prof.due", { date: dateLabel(feeDue) })}
                      </p>
                      <p className="mt-1 text-xl font-extrabold">{rupees(feeAmount)}</p>
                      <p className="text-xs text-muted">
                        {t("students.prof.paidBalance", { paid: rupees(feePaid), balance: rupees(balanceOf({ amount: feeAmount, paid: feePaid })) })}
                      </p>
                    </div>
                    <Chip tone={FEE_TONE[status]}>
                      <IndianRupee size={11} /> {t(`fees.status.${status}`)}
                    </Chip>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {can(viewer, "bills.create") && (
                      <Link href={`/billing/new?student=${student.id}`} className="btn btn-primary">
                        <ReceiptText size={15} /> {t("students.prof.makeBill")}
                      </Link>
                    )}
                    <Link href={`/calls?student=${student.id}`} className="btn btn-soft">
                      <PhoneCall size={15} /> {t("students.prof.callParent")}
                    </Link>
                  </div>
                  <Link href={`/fees/${student.id}`} className="mt-2 block text-center text-xs font-bold text-primary">
                    {t("students.prof.ledgerLink")}
                  </Link>
                </Card>
              </Section>
            )}

            {seeMarksheets && (
              <Section title={t("students.prof.documents")}>
                <Card className="divide-y divide-line">
                  {details.marksheets.length ? (
                    details.marksheets.map((m) => (
                      <div key={m.id} className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FileText size={16} className="shrink-0 text-muted" />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-[14px] font-semibold">{t("students.prof.marksheet", { year: m.year_label })}</p>
                            <p className="text-xs text-muted">{t("students.prof.typed", { pct: m.typed_percentage !== null ? `${Number(m.typed_percentage)}%` : "—" })}</p>
                          </div>
                          <Chip tone={AI_CHECK_TONE[m.ai_check_result]}>{t(`students.ai.${m.ai_check_result}`)}</Chip>
                        </div>
                        {m.ai_note && <p className="mt-1 pl-6 text-xs text-muted">{m.ai_note}</p>}
                        <div className="mt-2 flex gap-3 pl-6">
                          {m.file_path && (
                            <a href={`/api/marksheets/${m.id}`} target="_blank" rel="noreferrer" className="text-xs font-bold text-primary">
                              {t("students.prof.openFile")}
                            </a>
                          )}
                          {canEdit && m.file_path && m.ai_check_result !== "matched" && (
                            <form action={recheckMarksheet}>
                              <input type="hidden" name="marksheet_id" value={m.id} />
                              <button className="flex items-center gap-1 text-xs font-bold text-primary">
                                <RefreshCw size={12} /> {t("students.prof.checkAgain")}
                              </button>
                            </form>
                          )}
                          {canEdit && (
                            <Link href={`/students/${student.id}/edit`} className="text-xs font-bold text-primary">
                              {t("students.prof.betterPhoto")}
                            </Link>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="px-4 py-3 text-sm text-muted">{t("students.prof.noMarksheets")}</p>
                  )}
                  {details.consent && (
                    <p className="px-4 py-3 text-xs text-muted">
                      {t("students.prof.consentBy", { name: details.consent.given_by, date: dateLabel(details.consent.given_at.slice(0, 10)) })}
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
