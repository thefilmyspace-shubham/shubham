import "server-only";
import { z } from "zod";
import type { BulkResult } from "@/components/BulkBar";
import type { DictKey } from "./i18n";
import { getT } from "./i18n/server";

/** Only real ids, no repeats, at most 500 at once. */
export function cleanIds(ids: unknown): string[] {
  if (!Array.isArray(ids)) return [];
  return [...new Set(ids.filter((id): id is string => z.string().uuid().safeParse(id).success))].slice(0, 500);
}

/** "3 deleted." or "3 deleted. 2 could not be deleted: marks are entered". */
export async function bulkResult(done: number, skipped = 0, why?: DictKey): Promise<BulkResult> {
  const { t } = await getT();
  if (!skipped) return { ok: true, message: t("core.bulk.done", { n: done }) };
  return { ok: done > 0, message: t("core.bulk.doneSkipped", { n: done, m: skipped, why: why ? t(why) : "" }) };
}

export async function noAccess(): Promise<BulkResult> {
  const { t } = await getT();
  return { ok: false, message: t("core.bulk.noAccess") };
}
