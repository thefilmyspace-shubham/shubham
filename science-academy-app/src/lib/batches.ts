import "server-only";
import { cache } from "react";
import { adminClient } from "./supabase/admin";
import { boardName } from "./ids";
import { visibleBatchIds, type Viewer } from "./auth";
import type { Batch } from "./types";

/** "PCB · 8:00 AM" */
export function batchShort(b: Pick<Batch, "name" | "start_time">): string {
  return b.start_time ? `${b.name} · ${b.start_time}` : b.name;
}

/** "MP Board 9 · PCB · 8:00 AM" */
export function batchLabel(b: Pick<Batch, "board" | "class" | "name" | "start_time">): string {
  return `${boardName(b.board)} ${b.class} · ${batchShort(b)}`;
}

/** Board, then class, then batch name, then time. */
export function sortBatches<T extends Pick<Batch, "board" | "class" | "name" | "start_time">>(list: T[]): T[] {
  return [...list].sort(
    (a, b) =>
      a.board.localeCompare(b.board) ||
      a.class - b.class ||
      a.name.localeCompare(b.name) ||
      (a.start_time ?? "").localeCompare(b.start_time ?? ""),
  );
}

export const allBatches = cache(async (includeInactive = false): Promise<Batch[]> => {
  let q = adminClient().from("batches").select("*");
  if (!includeInactive) q = q.eq("active", true);
  const { data } = await q;
  return sortBatches((data ?? []) as Batch[]);
});

/** Batches this person may see (Faculty: own batches). */
export async function batchesFor(viewer: Viewer): Promise<Batch[]> {
  const all = await allBatches();
  const ids = visibleBatchIds(viewer);
  return ids === null ? all : all.filter((b) => ids.includes(b.id));
}

export function batchMap(list: Batch[]): Map<string, Batch> {
  return new Map(list.map((b) => [b.id, b]));
}
