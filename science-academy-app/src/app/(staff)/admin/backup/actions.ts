"use server";

import { revalidatePath } from "next/cache";
import { can, staffForApi } from "@/lib/auth";
import { runDailyBackup } from "@/lib/backup";
import { logActivity } from "@/lib/activity";

export type BackupState = { ok: boolean; message: string | null };

export async function makeBackupNow(): Promise<BackupState> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "admin.backup")) return { ok: false, message: "Only Admin can make backups." };
  try {
    const r = await runDailyBackup();
    await logActivity(viewer, "export.backup", { type: "backup" }, { made: true, rows: r.rows });
    revalidatePath("/admin/backup");
    return { ok: true, message: `Backup made: ${r.rows.toLocaleString("en-IN")} rows.` };
  } catch (err) {
    console.error("backup failed", err);
    return { ok: false, message: "The backup failed. Please try again." };
  }
}
