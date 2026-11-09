import { PAYMENT_MODE_LABEL, rupeesInWords } from "@/lib/fees";
import { boardName } from "@/lib/ids";
import { dateLabel, monthLabel, rupees } from "@/lib/format";
import type { AcademyDetails } from "@/lib/env";
import type { Invoice } from "@/lib/types";
import { Logo } from "@/components/Logo";

/** The fee receipt, laid out like the TFS bills. Used on screen and for printing. */
export function Receipt({ inv, academy, qr, copy }: { inv: Invoice; academy: AcademyDetails; qr: string | null; copy: string }) {
  const cancelled = inv.status === "cancelled";
  return (
    <div className="relative mx-auto max-w-[760px] overflow-hidden rounded-card bg-white p-5 text-[13.5px] shadow-card print:max-w-none print:rounded-none print:p-0 print:shadow-none sm:p-8">
      {cancelled && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <span className="-rotate-[20deg] rounded-xl border-4 border-danger/60 px-6 py-2 text-5xl font-extrabold tracking-widest text-danger/50">CANCELLED</span>
        </div>
      )}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
        <div>
          <Logo size={46} />
          <p className="mt-2 text-xs text-muted">
            {academy.address}, {academy.city}
          </p>
          <p className="text-xs text-muted">Phone {academy.phone}</p>
        </div>
        <div className="text-right">
          <p className="text-xl font-extrabold tracking-tight text-navy">Fee Receipt</p>
          <p className="text-[15px] font-bold text-primary">{inv.number}</p>
          <p className="text-xs text-muted">Date: {dateLabel(inv.paid_on)}</p>
          <p className="mt-1 inline-block rounded-full bg-field px-2 py-0.5 text-[11px] font-bold text-muted">{copy}</p>
        </div>
      </div>

      <div className="grid gap-x-6 gap-y-1.5 py-4 sm:grid-cols-2">
        <Field label="Student" value={inv.student_name} />
        <Field label="Student ID" value={inv.student_code} />
        <Field label="Class" value={`${inv.class} · ${boardName(inv.board)}`} />
        <Field label="Fee month" value={monthLabel(inv.month)} />
      </div>

      <table className="w-full border-y border-line">
        <tbody className="divide-y divide-line">
          <AmountRow label="Fee for the month" value={rupees(inv.fee_amount)} />
          <AmountRow label="Paid earlier this month" value={rupees(inv.paid_before)} />
          <AmountRow label="Received now" value={rupees(inv.received)} strong />
          <AmountRow label="Balance after this payment" value={rupees(inv.balance_after)} strong />
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted italic">Received: {rupeesInWords(inv.received)}</p>

      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
        <p>
          <span className="text-muted">Payment mode: </span>
          {(["upi", "bank", "cash"] as const).map((m) => (
            <span key={m} className="mr-3 inline-flex items-center gap-1 font-semibold">
              <span className={`inline-grid h-3.5 w-3.5 place-items-center rounded-sm border ${inv.modes.includes(m) ? "border-navy bg-navy text-[9px] text-white" : "border-faint"}`}>
                {inv.modes.includes(m) ? "✓" : ""}
              </span>
              {PAYMENT_MODE_LABEL[m]}
            </span>
          ))}
        </p>
        {inv.reference && (
          <p>
            <span className="text-muted">Reference: </span>
            <span className="font-semibold">{inv.reference}</span>
          </p>
        )}
      </div>

      <div className="mt-5 flex flex-wrap items-start justify-between gap-4 rounded-field bg-field p-4 print:bg-white print:border print:border-line">
        <div className="space-y-0.5 text-[12.5px]">
          <p className="mb-1 text-[13px] font-bold text-navy">Pay by UPI or bank transfer</p>
          <Field label="UPI ID" value={academy.upiId} small />
          <Field label="Bank" value={academy.bankName} small />
          <Field label="Account name" value={academy.accountName} small />
          <Field label="Account no." value={academy.accountNumber} small />
          <Field label="IFSC" value={academy.ifsc} small />
        </div>
        {qr ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={qr} alt={`UPI QR code for ${academy.upiId}`} width={116} height={116} className="rounded-md bg-white p-1" />
        ) : (
          <div className="grid h-[116px] w-[116px] place-items-center rounded-md border-2 border-dashed border-faint bg-white text-center text-[11px] font-bold text-faint">[UPI QR CODE]</div>
        )}
      </div>

      {cancelled && <p className="mt-3 text-sm font-bold text-danger">Cancelled: {inv.cancelled_reason}</p>}

      <div className="mt-10 flex items-end justify-between text-xs text-muted">
        <p>Fees are due on the 5th of every month.</p>
        <div className="text-center">
          <div className="mb-1 w-44 border-t border-muted" />
          Authorised signature
        </div>
      </div>
      <p className="mt-4 hidden text-center text-[10.5px] text-faint print:block">Powered by TFS · The First Solutions</p>
    </div>
  );
}

function Field({ label, value, small = false }: { label: string; value: string; small?: boolean }) {
  return (
    <p className="flex gap-2">
      <span className={`shrink-0 text-muted ${small ? "w-24" : "w-24"}`}>{label}</span>
      <span className="font-semibold text-fg">{value}</span>
    </p>
  );
}

function AmountRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <tr>
      <td className={`py-2 ${strong ? "font-bold text-navy" : ""}`}>{label}</td>
      <td className={`py-2 text-right ${strong ? "text-[15px] font-extrabold text-navy" : "font-semibold"}`}>{value}</td>
    </tr>
  );
}
