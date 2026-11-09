"use client";

import { useActionState, useRef, useState, useTransition } from "react";
import { LoaderCircle, Search, X } from "lucide-react";
import { billPreview } from "@/lib/billing-calc";
import { boardName } from "@/lib/ids";
import { dateLabel, rupees } from "@/lib/format";
import { createBill, loadBillMonth, searchStudentsForBill, type BillFormState, type MonthInfo, type StudentHit } from "../actions";

const MODES = [
  { key: "upi", label: "UPI" },
  { key: "bank", label: "Bank transfer" },
  { key: "cash", label: "Cash" },
] as const;

export function BillForm({
  initialStudent,
  initialMonth,
  initialInfo,
  today,
}: {
  initialStudent: StudentHit | null;
  initialMonth: string;
  initialInfo: MonthInfo | null;
  today: string;
}) {
  const startFee = initialInfo?.amount ?? initialStudent?.monthlyFee ?? 0;
  const startLeft = Math.max(0, startFee - (initialInfo?.paid ?? 0));
  const [student, setStudent] = useState<StudentHit | null>(initialStudent);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<StudentHit[]>([]);
  const [searching, startSearch] = useTransition();
  const [month, setMonth] = useState(initialMonth);
  const [info, setInfo] = useState<MonthInfo | null>(initialInfo);
  const [loadingMonth, startLoad] = useTransition();
  const [fee, setFee] = useState(startFee ? String(startFee) : "");
  const [received, setReceived] = useState(startLeft ? String(startLeft) : "");
  const [modes, setModes] = useState<string[]>([]);
  const [state, submit, pending] = useActionState<BillFormState, FormData>(createBill, null);
  const searchSeq = useRef(0);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadSeq = useRef(0);

  // Search as the user types.
  function onQuery(text: string) {
    setQuery(text);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    const seq = ++searchSeq.current;
    if (text.trim().length < 2) {
      setHits([]);
      return;
    }
    searchTimer.current = setTimeout(() => {
      startSearch(async () => {
        const res = await searchStudentsForBill(text);
        if (seq === searchSeq.current) setHits(res);
      });
    }, 250);
  }

  // The month's fee and earlier payments, for the live balance.
  function loadMonth(s: StudentHit | null, m: string) {
    const seq = ++loadSeq.current;
    if (!s || !/^\d{4}-\d{2}$/.test(m)) {
      setInfo(null);
      return;
    }
    startLoad(async () => {
      const res = await loadBillMonth(s.id, `${m}-01`);
      if (seq !== loadSeq.current) return;
      setInfo(res);
      const amount = res?.amount ?? s.monthlyFee;
      setFee(amount ? String(amount) : "");
      const left = Math.max(0, (amount || 0) - (res?.paid ?? 0));
      setReceived(left ? String(left) : "");
    });
  }

  const preview = billPreview(Number(fee), info?.paid ?? 0, Number(received));

  return (
    <form action={submit} className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_340px]">
      <div className="space-y-4 rounded-card bg-card p-4 shadow-card lg:p-5">
        {/* Student */}
        <div>
          <span className="label">Student</span>
          {student ? (
            <div className="flex items-center gap-3 rounded-field border border-primary bg-primary-soft px-3 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="font-bold text-navy">{student.name}</p>
                <p className="text-xs text-muted">
                  {student.code} · Class {student.cls} · {boardName(student.board)}
                  {student.earlierId ? ` · earlier ${student.earlierId}` : ""}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setStudent(null);
                  loadMonth(null, month);
                }}
                className="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-white"
                aria-label="Change student"
              >
                <X size={17} />
              </button>
              <input type="hidden" name="studentId" value={student.id} />
            </div>
          ) : (
            <div className="relative">
              <Search size={16} className="absolute top-3.5 left-3 text-faint" />
              <input
                className="field pl-9"
                placeholder="Search by student ID (MP9-025-26) or name"
                value={query}
                autoFocus
                onChange={(e) => onQuery(e.target.value)}
              />
              {searching && <LoaderCircle size={16} className="absolute top-3.5 right-3 animate-spin text-faint" />}
              {hits.length > 0 && (
                <div className="mt-1 divide-y divide-line overflow-hidden rounded-field border border-line bg-card">
                  {hits.map((h) => (
                    <button
                      key={h.id}
                      type="button"
                      onClick={() => {
                        setStudent(h);
                        setQuery("");
                        setHits([]);
                        loadMonth(h, month);
                      }}
                      className="block w-full px-3 py-2 text-left hover:bg-field"
                    >
                      <span className="block font-semibold">{h.name}</span>
                      <span className="block text-xs text-muted">
                        {h.code} · Class {h.cls} · {boardName(h.board)}
                        {h.earlierId ? ` · earlier ID ${h.earlierId}` : ""}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              {!searching && query.trim().length >= 2 && hits.length === 0 && <p className="mt-1 text-xs text-muted">No student found.</p>}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span className="label">Fee month</span>
            <input type="month" name="month" className="field" value={month} onChange={(e) => {
                setMonth(e.target.value);
                loadMonth(student, e.target.value);
              }} required />
          </label>
          <label>
            <span className="label">Date of payment</span>
            <input type="date" name="paidOn" className="field" defaultValue={today} max={today} required />
          </label>
          <label>
            <span className="label">Fee amount (₹)</span>
            <input type="number" name="fee" className="field" min={1} step="0.01" inputMode="decimal" value={fee} onChange={(e) => setFee(e.target.value)} required />
          </label>
          <label>
            <span className="label">Amount received now (₹)</span>
            <input
              type="number"
              name="received"
              className="field text-lg font-bold"
              min={1}
              step="0.01"
              inputMode="decimal"
              value={received}
              onChange={(e) => setReceived(e.target.value)}
              required
            />
          </label>
        </div>

        <fieldset>
          <legend className="label">Payment mode (tick by hand)</legend>
          <div className="flex flex-wrap gap-2">
            {MODES.map((m) => {
              const on = modes.includes(m.key);
              return (
                <label key={m.key} className={`flex cursor-pointer items-center gap-2 rounded-field border px-3 py-2 text-[14px] font-semibold ${on ? "border-primary bg-primary-soft text-primary" : "border-line bg-card"}`}>
                  <input
                    type="checkbox"
                    name="modes"
                    value={m.key}
                    checked={on}
                    onChange={() => setModes((prev) => (on ? prev.filter((x) => x !== m.key) : [...prev, m.key]))}
                    className="h-4 w-4 accent-[var(--color-primary)]"
                  />
                  {m.label}
                </label>
              );
            })}
          </div>
          <p className="mt-1 text-xs text-muted">The app does not check UPI payments by itself. Tick only after you have seen the money.</p>
        </fieldset>

        <label className="block">
          <span className="label">Transaction reference (UTR / cheque no.)</span>
          <input name="reference" className="field" placeholder={modes.includes("cash") && modes.length === 1 ? "Not needed for cash" : "e.g. 431298765432"} maxLength={100} />
        </label>
      </div>

      {/* Live summary */}
      <div className="space-y-3">
        <div className="rounded-card bg-card p-4 shadow-card">
          <p className="text-sm font-bold text-navy">This month so far</p>
          {loadingMonth ? (
            <p className="mt-2 flex items-center gap-2 text-sm text-muted">
              <LoaderCircle size={14} className="animate-spin" /> Loading…
            </p>
          ) : !student ? (
            <p className="mt-2 text-sm text-muted">Choose a student.</p>
          ) : info && info.bills.length > 0 ? (
            <ul className="mt-2 space-y-1.5 text-sm">
              {info.bills.map((b) => (
                <li key={b.id} className="flex justify-between gap-2">
                  <span className={b.status === "cancelled" ? "text-faint line-through" : ""}>
                    {b.number} · {dateLabel(b.paidOn)}
                  </span>
                  <span className={`font-semibold ${b.status === "cancelled" ? "text-faint line-through" : ""}`}>{rupees(b.received)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted">No payment yet for this month.</p>
          )}
        </div>

        <div className="rounded-card bg-navy p-4 text-white shadow-card">
          <Row label="Fee" value={rupees(preview.fee)} />
          <Row label="Paid earlier" value={rupees(preview.paidBefore)} />
          <Row label="Balance before" value={rupees(preview.balanceBefore)} />
          <Row label="Received now" value={rupees(preview.received)} strong />
          <div className="my-2 border-t border-white/20" />
          <Row label="Balance after" value={rupees(preview.balanceAfter)} strong />
        </div>

        {student && preview.error && Number(received) > 0 && <p className="text-sm font-semibold text-danger">{preview.error}</p>}
        {state?.error && <p className="text-sm font-semibold text-danger">{state.error}</p>}
        <button className="btn btn-primary w-full py-3 text-[15px]" disabled={pending || !student || Boolean(preview.error) || modes.length === 0 || loadingMonth}>
          {pending && <LoaderCircle size={17} className="animate-spin" />} Make bill
        </button>
        <p className="text-center text-xs text-muted">The invoice number is given when you press Make bill. Bills are never deleted.</p>
      </div>
    </form>
  );
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between py-0.5">
      <span className={`text-sm ${strong ? "font-bold" : "text-white/75"}`}>{label}</span>
      <span className={strong ? "text-lg font-extrabold" : "font-semibold"}>{value}</span>
    </div>
  );
}
