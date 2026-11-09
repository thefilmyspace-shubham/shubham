import { NextResponse, type NextRequest } from "next/server";
import { ensureLedgerForMonth } from "@/lib/fees-data";
import { runDailyReminders } from "@/lib/reminders";
import { runDailyBackup } from "@/lib/backup";
import { monthStart } from "@/lib/format";
import { logActivity } from "@/lib/activity";

export const maxDuration = 120;

/**
 * Once a day (vercel.json, 6:00 AM IST): this month's fee rows, reminders
 * (calls due, attendance not marked, escalations) and the Excel backup.
 * Each step runs even if an earlier one fails.
 */
export async function GET(req: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (!secret || req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "unauthorised" }, { status: 401 });
  }
  const now = new Date();
  const result: Record<string, unknown> = {};
  try {
    result.ledgerRows = await ensureLedgerForMonth(monthStart(now));
  } catch (err) {
    result.ledgerError = String(err);
  }
  try {
    result.reminders = await runDailyReminders(now);
  } catch (err) {
    result.remindersError = String(err);
  }
  try {
    result.backup = await runDailyBackup(now);
  } catch (err) {
    result.backupError = String(err);
  }
  await logActivity(null, "export.backup", { type: "cron" }, result);
  const failed = Object.keys(result).some((k) => k.endsWith("Error"));
  return NextResponse.json(result, { status: failed ? 500 : 200 });
}
