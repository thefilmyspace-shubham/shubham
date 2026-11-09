import "server-only";
import { academyDetails, upiIsPlaceholder } from "./env";
import { PAYMENT_MODE_LABEL, rupeesInWords } from "./fees";
import { boardName } from "./ids";
import { dateLabel, monthLabel } from "./format";
import { upiLink } from "./billing-calc";
import { qrDataUrl } from "./fees-data";
import { LINE, MARGIN, MUTED, NAVY, PAGE_W, drawFooters, drawHeader, newDoc, pdfRupees, toBuffer } from "./pdf";
import type { Invoice } from "./types";

export function billFileName(inv: Invoice): string {
  return `${inv.number} ${inv.student_name}.pdf`;
}

/**
 * The fee receipt as a PDF: an Office copy and a Parent copy on two pages.
 * Cancelled bills carry a CANCELLED stamp and the reason.
 */
export async function buildBillPdf(inv: Invoice, opts: { copies?: ("Office copy" | "Parent copy")[] } = {}): Promise<Buffer> {
  const a = academyDetails();
  const placeholderUpi = upiIsPlaceholder(a.upiId);
  const qr = placeholderUpi ? null : await qrDataUrl(upiLink(a.upiId));
  const copies = opts.copies ?? ["Office copy", "Parent copy"];
  const doc = newDoc();

  copies.forEach((copy, index) => {
    if (index > 0) doc.addPage();
    let y = drawHeader(doc, {
      title: "Fee Receipt",
      subtitle: copy,
      right: [inv.number, `Date: ${dateLabel(inv.paid_on)}`],
    });

    // Student block
    const rows: [string, string][] = [
      ["Student", inv.student_name],
      ["Student ID", inv.student_code],
      ["Class", `${inv.class} · ${boardName(inv.board)}`],
      ["Fee month", monthLabel(inv.month)],
    ];
    doc.setFontSize(10);
    for (const [k, v] of rows) {
      doc.setFont("helvetica", "normal");
      doc.setTextColor(...MUTED);
      doc.text(k, MARGIN, y);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(19, 26, 42);
      doc.text(v, MARGIN + 32, y);
      y += 6;
    }
    y += 3;

    // Amounts
    const amounts: [string, string, boolean][] = [
      ["Fee for the month", pdfRupees(inv.fee_amount), false],
      ["Paid earlier this month", pdfRupees(inv.paid_before), false],
      ["Received now", pdfRupees(inv.received), true],
      ["Balance after this payment", pdfRupees(inv.balance_after), true],
    ];
    const boxW = PAGE_W - MARGIN * 2;
    doc.setDrawColor(...LINE);
    doc.setLineWidth(0.4);
    doc.roundedRect(MARGIN, y, boxW, amounts.length * 8 + 4, 2, 2, "S");
    let ay = y + 7;
    for (const [k, v, strong] of amounts) {
      doc.setFont("helvetica", strong ? "bold" : "normal");
      doc.setFontSize(10.5);
      doc.setTextColor(...(strong ? NAVY : ([19, 26, 42] as [number, number, number])));
      doc.text(k, MARGIN + 4, ay);
      doc.text(v, MARGIN + boxW - 4, ay, { align: "right" });
      ay += 8;
    }
    y += amounts.length * 8 + 10;

    doc.setFont("helvetica", "italic");
    doc.setFontSize(9.5);
    doc.setTextColor(...MUTED);
    doc.text(`Received: ${rupeesInWords(inv.received)}`, MARGIN, y);
    y += 6;
    doc.setFont("helvetica", "normal");
    doc.setTextColor(19, 26, 42);
    const modes = inv.modes.map((m) => PAYMENT_MODE_LABEL[m]).join(", ");
    doc.text(`Payment mode: ${modes}${inv.reference ? `   ·   Reference: ${inv.reference}` : ""}`, MARGIN, y);
    y += 10;

    // How to pay
    doc.setDrawColor(...LINE);
    doc.line(MARGIN, y, PAGE_W - MARGIN, y);
    y += 7;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    doc.setTextColor(...NAVY);
    doc.text("Pay by UPI or bank transfer", MARGIN, y);
    const qrSize = 32;
    const qrX = PAGE_W - MARGIN - qrSize;
    if (qr) {
      doc.addImage(qr, "PNG", qrX, y - 4, qrSize, qrSize);
    } else {
      doc.setDrawColor(...MUTED);
      doc.setLineDashPattern([1.5, 1.5], 0);
      doc.rect(qrX, y - 4, qrSize, qrSize, "S");
      doc.setLineDashPattern([], 0);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(8);
      doc.setTextColor(...MUTED);
      doc.text("[UPI QR CODE]", qrX + qrSize / 2, y - 4 + qrSize / 2, { align: "center" });
    }
    y += 7;
    const bank: [string, string][] = [
      ["UPI ID", a.upiId],
      ["Bank", a.bankName],
      ["Account name", a.accountName],
      ["Account number", a.accountNumber],
      ["IFSC", a.ifsc],
    ];
    doc.setFontSize(9.5);
    for (const [k, v] of bank) {
      doc.setFont("helvetica", "normal");
      doc.setTextColor(...MUTED);
      doc.text(k, MARGIN, y);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(19, 26, 42);
      doc.text(v, MARGIN + 32, y);
      y += 5.5;
    }
    y += 16;

    // Signature
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(...MUTED);
    doc.line(PAGE_W - MARGIN - 50, y, PAGE_W - MARGIN, y);
    doc.text("Authorised signature", PAGE_W - MARGIN - 25, y + 4.5, { align: "center" });
    doc.text("Fees are due on the 5th of every month.", MARGIN, y + 4.5);

    if (inv.status === "cancelled") {
      doc.setTextColor(200, 50, 43);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(54);
      doc.text("CANCELLED", PAGE_W / 2, 150, { align: "center", angle: 25 });
      doc.setFontSize(10);
      doc.text(`Cancelled: ${inv.cancelled_reason ?? ""}`, MARGIN, y + 14);
    }
  });
  drawFooters(doc);
  return toBuffer(doc);
}
