"use client";

import { FeePlanFields, type FeePlanInitial } from "./FeePlanFields";
import { startTransition, useActionState, useMemo, useState } from "react";
import { AlertCircle, ArrowLeft, ArrowRight, FileText, LoaderCircle, ShieldCheck, Upload } from "lucide-react";
import { boardName, formatStudentId, sessionLabel } from "@/lib/ids";
import type { AiCheck, GuardianRelation } from "@/lib/types";
import { saveStudent, type SaveState } from "./actions";

export type BatchOption = { id: string; board: string; class: number; label: string };

export type FormInitial = {
  id: string;
  status: string;
  code: string | null;
  name: string;
  board: string;
  current_class: number;
  session_year: number;
  school: string | null;
  batch_id: string | null;
  father_name: string | null;
  mother_name: string | null;
  guardian_name: string | null;
  email: string | null;
  monthly_fee: number;
  feePlan: FeePlanInitial;
  mobiles: Partial<Record<GuardianRelation, { mobile: string; name: string | null }>>;
  loginRelation: GuardianRelation | null;
  marksheets: { id: string; year_label: string; file_name: string | null; typed_percentage: number | null; ai: AiCheck; note: string | null }[];
  consentGiven: boolean;
};

const STEP1_FIELDS = [
  "name",
  "board",
  "current_class",
  "session_year",
  "school",
  "batch_id",
  "father_name",
  "mother_name",
  "guardian_name",
  "email",
  "monthly_fee",
  "fee_due_day",
  "fee_schedule",
  "father_mobile",
  "mother_mobile",
  "guardian_mobile",
  "alternate_mobile",
  "login_relation",
];

const AI_LABEL: Record<AiCheck, string> = { pending: "Not checked", matched: "Matched", mismatch: "Mismatch", cant_read: "Can't read" };
const AI_TONE: Record<AiCheck, string> = {
  pending: "bg-field text-muted",
  matched: "bg-ok-soft text-ok",
  mismatch: "bg-danger-soft text-danger",
  cant_read: "bg-warn-soft text-warn",
};

function Err({ msg }: { msg?: string }) {
  return msg ? <p className="mt-1 text-xs font-semibold text-danger">{msg}</p> : null;
}

export function StudentForm({
  batches,
  nextRoll,
  defaultSession,
  consentText,
  initial,
}: {
  batches: BatchOption[];
  nextRoll: number;
  defaultSession: number;
  consentText: string;
  initial?: FormInitial;
}) {
  const [state, dispatch, pending] = useActionState<SaveState, FormData>(saveStudent, null);
  const registered = Boolean(initial && initial.status !== "draft");
  const [step, setStep] = useState<1 | 2>(1);
  const [board, setBoard] = useState(initial?.board ?? "");
  const [cls, setCls] = useState(initial ? String(initial.current_class) : "");
  const [session, setSession] = useState(String(initial?.session_year ?? defaultSession));
  const [batchId, setBatchId] = useState(initial?.batch_id ?? "");
  const [mobiles, setMobiles] = useState<Record<GuardianRelation, string>>({
    father: initial?.mobiles.father?.mobile ?? "",
    mother: initial?.mobiles.mother?.mobile ?? "",
    guardian: initial?.mobiles.guardian?.mobile ?? "",
    alternate: initial?.mobiles.alternate?.mobile ?? "",
  });
  const [login, setLogin] = useState<GuardianRelation | "">(initial?.loginRelation ?? "");
  const [fatherName, setFatherName] = useState(initial?.father_name ?? "");
  const [motherName, setMotherName] = useState(initial?.mother_name ?? "");
  const errors = state?.errors ?? {};

  // After a failed save, go back to step 1 when the problem is there (phone).
  const [seenState, setSeenState] = useState<SaveState>(null);
  if (state !== seenState) {
    setSeenState(state);
    if (state?.errors && Object.keys(state.errors).some((k) => STEP1_FIELDS.includes(k))) setStep(1);
  }

  const batchChoices = useMemo(() => batches.filter((b) => b.board === board && String(b.class) === cls), [batches, board, cls]);
  const sessionNum = Number(session);
  const idPreview =
    board && cls && Number.isFinite(sessionNum)
      ? registered && initial?.code
        ? initial.code
        : formatStudentId(board, Number(cls), nextRoll, sessionNum)
      : null;

  // Default year labels for the last two years' marksheets.
  const yearDefault = (back: number) => {
    if (!cls || !Number.isFinite(sessionNum)) return "";
    const start = 2000 + sessionNum - back;
    return `${start}-${String((start + 1) % 100).padStart(2, "0")} (Class ${Number(cls) - back})`;
  };

  const relRow = (rel: GuardianRelation, label: string, nameField?: React.ReactNode) => (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {nameField}
      <div className={nameField ? "" : "sm:col-span-2"}>
        <label className="label" htmlFor={`${rel}_mobile`}>
          {label} mobile
        </label>
        <div className="flex items-center gap-2">
          <input
            id={`${rel}_mobile`}
            name={`${rel}_mobile`}
            className="field"
            inputMode="numeric"
            placeholder="10 digit number"
            value={mobiles[rel]}
            onChange={(e) => {
              const v = e.target.value;
              setMobiles((m) => ({ ...m, [rel]: v }));
              if (!v.trim() && login === rel) setLogin("");
            }}
          />
          <label
            className={`flex shrink-0 cursor-pointer items-center gap-1.5 rounded-full border px-2.5 py-2 text-[12px] font-bold ${
              login === rel ? "border-primary bg-primary-soft text-primary" : "border-line text-muted"
            } ${mobiles[rel].trim() ? "" : "pointer-events-none opacity-40"}`}
          >
            <input
              type="radio"
              name="login_relation"
              value={rel}
              checked={login === rel}
              onChange={() => setLogin(rel)}
              disabled={!mobiles[rel].trim()}
              className="accent-[var(--color-primary)]"
            />
            Login
          </label>
        </div>
        <Err msg={errors[`${rel}_mobile`]} />
      </div>
    </div>
  );

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const submitter = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
        const fd = new FormData(e.currentTarget, submitter);
        startTransition(() => dispatch(fd));
      }}
      className="space-y-4"
      noValidate
    >
      {initial && <input type="hidden" name="student_id" value={initial.id} />}

      {/* Phone: two steps. Desktop: one page. */}
      <div className="flex items-center gap-2 lg:hidden">
        {[1, 2].map((n) => (
          <div key={n} className="flex flex-1 items-center gap-2">
            <span className={`grid h-6 w-6 place-items-center rounded-full text-xs font-extrabold ${step >= n ? "bg-primary text-white" : "bg-line text-muted"}`}>{n}</span>
            <span className={`text-xs font-bold ${step === n ? "text-navy" : "text-muted"}`}>{n === 1 ? "Student & parents" : "Marksheets & consent"}</span>
          </div>
        ))}
      </div>

      {state?.message && (
        <div className="flex items-center gap-2 rounded-field bg-danger-soft px-3 py-2.5 text-sm font-semibold text-danger">
          <AlertCircle size={16} /> {state.message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_380px]">
        <div className={`space-y-4 ${step === 1 ? "block" : "hidden"} lg:block`}>
          <section className="rounded-card bg-card p-4 shadow-card">
            <h2 className="mb-3 text-[15px] font-bold text-navy">Student</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="label" htmlFor="name">
                  Student name
                </label>
                <input id="name" name="name" className="field" defaultValue={initial?.name} autoComplete="off" />
                <Err msg={errors.name} />
              </div>
              <div>
                <label className="label" htmlFor="board">
                  Board
                </label>
                <select
                  id="board"
                  name="board"
                  className="field"
                  value={board}
                  onChange={(e) => {
                    setBoard(e.target.value);
                    setBatchId("");
                  }}
                >
                  <option value="">Choose</option>
                  <option value="CB">CBSE</option>
                  <option value="MP">MP Board</option>
                </select>
                <Err msg={errors.board} />
              </div>
              <div>
                <label className="label" htmlFor="current_class">
                  Class
                </label>
                <select
                  id="current_class"
                  name="current_class"
                  className="field"
                  value={cls}
                  onChange={(e) => {
                    setCls(e.target.value);
                    setBatchId("");
                  }}
                >
                  <option value="">Choose</option>
                  {[6, 7, 8, 9, 10, 11, 12].map((c) => (
                    <option key={c} value={c}>
                      Class {c}
                    </option>
                  ))}
                </select>
                <Err msg={errors.current_class} />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="school">
                  School name
                </label>
                <input id="school" name="school" className="field" defaultValue={initial?.school ?? ""} />
              </div>
              <div>
                <label className="label" htmlFor="batch_id">
                  Batch
                </label>
                <select id="batch_id" name="batch_id" className="field" value={batchId} onChange={(e) => setBatchId(e.target.value)} disabled={!board || !cls}>
                  <option value="">{!board || !cls ? "Choose board and class first" : batchChoices.length ? "Choose" : "No batch for this class yet"}</option>
                  {batchChoices.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.label}
                    </option>
                  ))}
                </select>
                <Err msg={errors.batch_id} />
              </div>
              <div>
                <label className="label" htmlFor="session_year">
                  Session year
                </label>
                <select id="session_year" name="session_year" className="field" value={session} onChange={(e) => setSession(e.target.value)}>
                  {[defaultSession - 1, defaultSession, defaultSession + 1].map((s) => (
                    <option key={s} value={s}>
                      {sessionLabel(s)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="email">
                  Parent&apos;s email (login code, bills and PDFs go here)
                </label>
                <input id="email" name="email" type="email" className="field" defaultValue={initial?.email ?? ""} />
                <Err msg={errors.email} />
              </div>
            </div>
          </section>

          <FeePlanFields initial={initial?.feePlan ?? null} errors={errors} locked={registered} studentId={initial?.id} />

          <section className="rounded-card bg-card p-4 shadow-card">
            <h2 className="text-[15px] font-bold text-navy">Parents and contact numbers</h2>
            <p className="mb-3 text-xs text-muted">Only one number can log in. Tap “Login” next to it. The others are for contact only.</p>
            <div className="space-y-3">
              {relRow(
                "father",
                "Father's",
                <div>
                  <label className="label" htmlFor="father_name">
                    Father&apos;s name
                  </label>
                  <input id="father_name" name="father_name" className="field" value={fatherName} onChange={(e) => setFatherName(e.target.value)} />
                </div>,
              )}
              {relRow(
                "mother",
                "Mother's",
                <div>
                  <label className="label" htmlFor="mother_name">
                    Mother&apos;s name
                  </label>
                  <input id="mother_name" name="mother_name" className="field" value={motherName} onChange={(e) => setMotherName(e.target.value)} />
                </div>,
              )}
              {relRow(
                "guardian",
                "Guardian's",
                <div>
                  <label className="label" htmlFor="guardian_name">
                    Guardian&apos;s name (optional)
                  </label>
                  <input id="guardian_name" name="guardian_name" className="field" defaultValue={initial?.guardian_name ?? ""} />
                </div>,
              )}
              {relRow(
                "alternate",
                "Alternate",
                <div>
                  <label className="label" htmlFor="alternate_name">
                    Alternate contact name (optional)
                  </label>
                  <input id="alternate_name" name="alternate_name" className="field" defaultValue={initial?.mobiles.alternate?.name ?? ""} />
                </div>,
              )}
              <Err msg={errors.login_relation} />
            </div>
          </section>

          <div className="flex justify-end lg:hidden">
            <button type="button" className="btn btn-primary" onClick={() => setStep(2)}>
              Next: marksheets <ArrowRight size={16} />
            </button>
          </div>
        </div>

        <div className={`space-y-4 ${step === 2 ? "block" : "hidden"} lg:block`}>
          <section className="rounded-card bg-navy p-4 text-white shadow-card">
            <p className="text-xs font-semibold text-white/70">{registered ? "Student ID" : "Student ID (preview)"}</p>
            <p className="mt-1 text-2xl font-extrabold tracking-tight">{idPreview ?? "Choose board and class"}</p>
            <p className="mt-1 text-xs text-white/70">
              {registered
                ? "The roll number never changes. The class and year in the ID change at promotion."
                : "The roll number is given when you press Register (next free number for the whole academy)."}
            </p>
            {board && cls && (
              <p className="mt-2 text-xs text-white/80">
                {boardName(board)} · Class {cls} · Session {Number.isFinite(sessionNum) ? sessionLabel(sessionNum) : ""}
              </p>
            )}
          </section>

          <section className="rounded-card bg-card p-4 shadow-card">
            <h2 className="text-[15px] font-bold text-navy">Marksheets (last two years)</h2>
            <p className="mb-3 text-xs text-muted">Upload a clear photo or PDF and type the percentage. The AI check compares the name and percentage. It never guesses.</p>
            <div className="space-y-4">
              {[0, 1].map((i) => {
                const ms = initial?.marksheets[i];
                return (
                  <div key={i} className="rounded-field border border-line p-3">
                    {ms && <input type="hidden" name={`ms${i}_id`} value={ms.id} />}
                    <div className="grid grid-cols-[1fr_96px] gap-2">
                      <div>
                        <label className="label" htmlFor={`ms${i}_year`}>
                          Year
                        </label>
                        <input
                          id={`ms${i}_year`}
                          name={`ms${i}_year`}
                          className="field"
                          defaultValue={ms?.year_label ?? ""}
                          placeholder={yearDefault(i + 1) || `Year ${i + 1}`}
                          key={ms ? ms.id : `y-${cls}-${session}`}
                        />
                      </div>
                      <div>
                        <label className="label" htmlFor={`ms${i}_pct`}>
                          Percentage
                        </label>
                        <input
                          id={`ms${i}_pct`}
                          name={`ms${i}_pct`}
                          className="field"
                          inputMode="decimal"
                          placeholder="87.4"
                          defaultValue={ms?.typed_percentage ?? ""}
                        />
                      </div>
                    </div>
                    {ms?.file_name && (
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                        <FileText size={14} className="text-muted" />
                        <span className="max-w-[160px] truncate font-semibold">{ms.file_name}</span>
                        <span className={`rounded-full px-2 py-0.5 font-bold ${AI_TONE[ms.ai]}`}>{AI_LABEL[ms.ai]}</span>
                        {ms.note && <span className="w-full text-muted">{ms.note}</span>}
                      </div>
                    )}
                    <label className="mt-2 flex cursor-pointer items-center gap-2 rounded-field border border-dashed border-line px-3 py-2.5 text-sm font-semibold text-primary hover:border-primary">
                      <Upload size={16} />
                      <span>{ms?.file_name ? "Replace file" : "Upload photo or PDF"}</span>
                      <input
                        type="file"
                        name={`ms${i}_file`}
                        accept="image/jpeg,image/png,image/webp,image/heic,application/pdf"
                        className="min-w-0 flex-1 text-xs text-muted file:hidden"
                      />
                    </label>
                    <Err msg={errors[`ms${i}_file`]} />
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-card bg-card p-4 shadow-card">
            <h2 className="mb-2 flex items-center gap-2 text-[15px] font-bold text-navy">
              <ShieldCheck size={17} className="text-green" /> Consent
            </h2>
            {initial?.consentGiven ? (
              <p className="text-sm text-ok">Consent is on record.</p>
            ) : (
              <>
                <label className="flex items-start gap-2.5 text-[13px]">
                  <input type="checkbox" name="consent" className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--color-primary)]" />
                  <span>{consentText}</span>
                </label>
                <Err msg={errors.consent} />
                <div className="mt-3">
                  <label className="label" htmlFor="consent_by">
                    Consent given by (parent or guardian name)
                  </label>
                  <input id="consent_by" name="consent_by" className="field" key={fatherName || motherName} defaultValue={fatherName || motherName} />
                  <Err msg={errors.consent_by} />
                </div>
              </>
            )}
            {initial?.consentGiven && <input type="hidden" name="consent" value="true" />}
            {initial?.consentGiven && <input type="hidden" name="consent_by" value="on record" />}
            <p className="mt-3 text-xs text-muted">No student photo is collected.</p>
          </section>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <button type="button" className="btn btn-ghost mr-auto lg:hidden" onClick={() => setStep(1)}>
              <ArrowLeft size={16} /> Back
            </button>
            {!registered && (
              <button type="submit" name="intent" value="draft" className="btn btn-ghost" disabled={pending}>
                Save as draft
              </button>
            )}
            <button type="submit" name="intent" value="register" className="btn btn-primary" disabled={pending}>
              {pending && <LoaderCircle size={16} className="animate-spin" />}
              {registered ? "Save changes" : "Register"}
            </button>
          </div>
          {pending && <p className="text-right text-xs text-muted">Saving and checking marksheets… this can take a few seconds.</p>}
        </div>
      </div>
    </form>
  );
}
