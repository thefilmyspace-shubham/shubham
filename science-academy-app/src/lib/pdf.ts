import "server-only";
import { jsPDF } from "jspdf";
import { academyDetails } from "./env";
import { LOGO_JPEG_BASE64, LOGO_RATIO } from "./brand-logo";

// Server-side PDFs (bills, rankings, AI comparisons) share this look:
// Science Academy header, a title, tables, and the TFS footer on every page.
// Built-in PDF fonts have no ₹ sign, so amounts use "Rs." in PDFs.

export const NAVY: [number, number, number] = [11, 60, 93];
export const BLUE: [number, number, number] = [10, 124, 196];
export const GREEN: [number, number, number] = [106, 162, 50];
export const MUTED: [number, number, number] = [95, 107, 125];
export const LINE: [number, number, number] = [228, 232, 239];

export const PAGE_W = 210;
export const PAGE_H = 297;
export const MARGIN = 14;

/** Rs. 35,200 */
export function pdfRupees(amount: number | string): string {
  return `Rs. ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(amount) || 0)}`;
}

/** Draws the Science Academy mark and name. Returns the y below it. */
export function drawHeader(doc: jsPDF, opts: { title: string; subtitle?: string; right?: string[]; y?: number }): number {
  const a = academyDetails();
  const y = opts.y ?? MARGIN;
  // The logo (mark + "SCIENCE ACADEMY / WE BELIEVE IN QUALITY"), 11 mm tall.
  const logoH = 11;
  doc.addImage(LOGO_JPEG_BASE64, "JPEG", MARGIN, y, logoH * LOGO_RATIO, logoH);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor(...MUTED);
  doc.text(`${a.address}, ${a.city}  ·  Phone ${a.phone}`, MARGIN, y + 15.5);

  if (opts.right?.length) {
    doc.setFontSize(9);
    doc.setTextColor(...NAVY);
    opts.right.forEach((line, i) => {
      doc.setFont("helvetica", i === 0 ? "bold" : "normal");
      doc.text(line, PAGE_W - MARGIN, y + 5 + i * 4.6, { align: "right" });
    });
  }

  doc.setDrawColor(...LINE);
  doc.setLineWidth(0.4);
  doc.line(MARGIN, y + 19, PAGE_W - MARGIN, y + 19);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.setTextColor(...NAVY);
  doc.text(opts.title, MARGIN, y + 27);
  let below = y + 29;
  if (opts.subtitle) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    doc.setTextColor(...MUTED);
    doc.text(opts.subtitle, MARGIN, y + 32.5);
    below = y + 35;
  }
  return below + 3;
}

/** "Powered by TFS · The First Solutions" and page numbers on every page. */
export function drawFooters(doc: jsPDF): void {
  const pages = doc.getNumberOfPages();
  for (let i = 1; i <= pages; i++) {
    doc.setPage(i);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...MUTED);
    doc.text("Powered by TFS · The First Solutions", PAGE_W / 2, PAGE_H - 8, { align: "center" });
    if (pages > 1) doc.text(`Page ${i} of ${pages}`, PAGE_W - MARGIN, PAGE_H - 8, { align: "right" });
  }
}

export type Column = { header: string; width: number; align?: "left" | "right" | "center" };

/** A simple table with a header row; continues on new pages. Returns the y below it. */
export function drawTable(doc: jsPDF, columns: Column[], rows: string[][], startY: number, opts: { zebra?: boolean; bold?: number[] } = {}): number {
  const rowH = 7;
  let y = startY;
  const header = () => {
    doc.setFillColor(...NAVY);
    doc.rect(MARGIN, y, PAGE_W - MARGIN * 2, rowH, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8.8);
    doc.setTextColor(255, 255, 255);
    let x = MARGIN;
    for (const c of columns) {
      drawCell(doc, c.header, x, y, c);
      x += c.width;
    }
    y += rowH;
  };
  header();
  rows.forEach((row, ri) => {
    if (y + rowH > PAGE_H - 18) {
      doc.addPage();
      y = MARGIN;
      header();
    }
    if (opts.zebra !== false && ri % 2 === 1) {
      doc.setFillColor(246, 248, 251);
      doc.rect(MARGIN, y, PAGE_W - MARGIN * 2, rowH, "F");
    }
    doc.setFont("helvetica", opts.bold?.includes(ri) ? "bold" : "normal");
    doc.setFontSize(8.8);
    doc.setTextColor(19, 26, 42);
    let x = MARGIN;
    columns.forEach((c, ci) => {
      drawCell(doc, row[ci] ?? "", x, y, c);
      x += c.width;
    });
    y += rowH;
  });
  doc.setDrawColor(...LINE);
  doc.line(MARGIN, y, PAGE_W - MARGIN, y);
  return y + 4;
}

function drawCell(doc: jsPDF, text: string, x: number, y: number, c: Column) {
  const pad = 2;
  const max = c.width - pad * 2;
  let t = text;
  while (t.length > 1 && doc.getTextWidth(t) > max) t = t.slice(0, -2) + "…";
  const tx = c.align === "right" ? x + c.width - pad : c.align === "center" ? x + c.width / 2 : x + pad;
  doc.text(t, tx, y + 4.8, { align: c.align ?? "left" });
}

export function newDoc(): jsPDF {
  return new jsPDF({ unit: "mm", format: "a4", compress: true });
}

export function toBuffer(doc: jsPDF): Buffer {
  return Buffer.from(doc.output("arraybuffer"));
}

/** Response headers for a PDF download. */
export function pdfHeaders(fileName: string, inline = false): HeadersInit {
  const safe = fileName.replace(/[^\w.\- ]+/g, "_");
  return {
    "content-type": "application/pdf",
    "content-disposition": `${inline ? "inline" : "attachment"}; filename="${safe}"`,
    "cache-control": "no-store",
  };
}
