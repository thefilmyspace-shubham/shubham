"use server";

import { revalidatePath } from "next/cache";
import { can, staffForApi } from "@/lib/auth";
import { runDailyBackup } from "@/lib/backup";
import { logActivity } from "@/lib/activity";
import { getT } from "@/lib/i18n/server";

export type BackupState = { ok: boolean; message: string | null };

export async function makeBackupNow(): Promise<BackupState> {
  const viewer = await staffForApi();
  const { t } = await getT();
  if (!viewer || !can(viewer, "admin.backup")) return { ok: false, message: t("admin.backup.onlyAdmin") };
  try {
    const r = await runDailyBackup();
    await logActivity(viewer, "export.backup", { type: "backup" }, { made: true, rows: r.rows });
    revalidatePath("/admin/backup");
    return { ok: true, message: t("admin.backup.made", { n: r.rows.toLocaleString("en-IN") }) };
  } catch (err) {
    console.error("backup failed", err);
    return { ok: false, message: t("admin.backup.failed") };
  }
}
