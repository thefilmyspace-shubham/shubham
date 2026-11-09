import "server-only";
import ExcelJS from "exceljs";
import { adminClient } from "./supabase/admin";
import { saveFile } from "./storage";
import { addDays, todayIst } from "./format";

// The daily Excel backup: one sheet per table. OTP codes, login sessions and
// auth ids are left out on purpose (secrets, not data).

type Sheet = { table: string; name: string; select?: string; since?: { column: string; days: number }; order?: string };

const SHEETS: Sheet[] = [
  { table: "users", name: "Users", select: "id, staff_id, role, name, mobile, email, status, created_at", order: "created_at" },
  { table: "batches", name: "Batches", order: "created_at" },
  { table: "faculty_batches", name: "Faculty batches", order: "batch_id" },
  { table: "students", name: "Students", order: "roll_number" },
  { table: "student_id_history", name: "ID history", order: "valid_from" },
  { table: "guardians", name: "Guardians", order: "student_id" },
  { table: "marksheets", name: "Marksheets", select: "id, student_id, year_label, file_name, typed_percentage, ai_check_result, ai_read_name, ai_read_percentage, ai_note, created_at", order: "created_at" },
  { table: "consents", name: "Consents", order: "given_at" },
  { table: "attendance", name: "Attendance", order: "date" },
  { table: "fees_ledger", name: "Fees ledger", order: "month" },
  { table: "invoices", name: "Bills", order: "created_at" },
  { table: "call_log", name: "Call log", order: "created_at" },
  { table: "fee_reminders", name: "Fee reminders", order: "created_at" },
  { table: "timetable_entries", name: "Timetable", order: "batch_id" },
  { table: "tests", name: "Tests", order: "date" },
  { table: "marks", name: "Marks", order: "test_id" },
  { table: "messages", name: "Group messages", order: "created_at" },
  { table: "activity_log", name: "Activity log (90 days)", since: { column: "created_at", days: 90 }, order: "created_at" },
];

const PAGE = 1000;

async function fetchAll(sheet: Sheet, today: string): Promise<Record<string, unknown>[]> {
  const db = adminClient();
  const out: Record<string, unknown>[] = [];
  for (let from = 0; ; from += PAGE) {
    let q = db.from(sheet.table).select(sheet.select ?? "*");
    if (sheet.since) q = q.gte(sheet.since.column, addDays(today, -sheet.since.days));
    if (sheet.order) q = q.order(sheet.order, { ascending: true });
    const { data, error } = await q.range(from, from + PAGE - 1);
    if (error) throw new Error(`backup: ${sheet.table}: ${error.message}`);
    const rows = (data ?? []) as unknown as Record<string, unknown>[];
    out.push(...rows);
    if (rows.length < PAGE) break;
  }
  return out;
}

function cell(v: unknown): ExcelJS.CellValue {
  if (v === null || v === undefined) return null;
  if (typeof v === "number" || typeof v === "boolean") return v;
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export async function buildBackupWorkbook(now = new Date()): Promise<{ buffer: Buffer; rows: number }> {
  const today = todayIst(now);
  const wb = new ExcelJS.Workbook();
  wb.creator = "Science Academy app";
  wb.created = now;
  let total = 0;
  for (const sheet of SHEETS) {
    const rows = await fetchAll(sheet, today);
    total += rows.length;
    const ws = wb.addWorksheet(sheet.name.slice(0, 31));
    const columns = rows.length ? Object.keys(rows[0]) : (sheet.select?.split(",").map((s) => s.trim()) ?? ["(empty)"]);
    ws.columns = columns.map((c) => ({ header: c, key: c, width: Math.min(40, Math.max(10, c.length + 2)) }));
    ws.getRow(1).font = { bold: true };
    ws.views = [{ state: "frozen", ySplit: 1 }];
    for (const r of rows) ws.addRow(Object.fromEntries(columns.map((c) => [c, cell(r[c])])));
  }
  const buffer = Buffer.from(await wb.xlsx.writeBuffer());
  return { buffer, rows: total };
}

/** Builds today's backup, stores it in the private "backups" bucket and records it. */
export async function runDailyBackup(now = new Date()): Promise<{ path: string; rows: number }> {
  const { buffer, rows } = await buildBackupWorkbook(now);
  const day = todayIst(now);
  const path = await saveFile("backups", day.slice(0, 7), {
    name: `science-academy-backup-${day}.xlsx`,
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    data: buffer,
  });
  await adminClient().from("backups").insert({ file_path: path, rows_total: rows });
  return { path, rows };
}
