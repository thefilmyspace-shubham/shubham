import "server-only";
import { adminClient } from "./supabase/admin";
import { can, visibleBatchIds, type Viewer } from "./auth";
import { allBatches, batchLabel, batchMap } from "./batches";
import { parseSearchQuery, type SearchQuery } from "./search";
import type { Student } from "./types";

export type SearchHit = {
  student: Pick<Student, "id" | "name" | "code" | "board" | "current_class" | "status" | "batch_id" | "school">;
  batch: string | null;
  earlierIds: string[];
  matchedBy: "id" | "earlier_id" | "name" | "mobile" | "class";
};

export type SearchResult =
  | { ok: true; query: SearchQuery; hits: SearchHit[]; truncated: boolean }
  | { ok: false; /** Dictionary key, shown in the reader's language. */ error: "students.search.noAccess" | "students.search.typeSomething" | "students.search.noMobile" };

const LIMIT = 60;
const COLS = "id, name, code, board, current_class, status, batch_id, school";

/**
 * Runs a home search for this viewer. Faculty only find students of their own
 * batches; searching by a parent's number needs the "see parents' numbers"
 * permission, and the number itself is never shown in the results.
 */
export async function searchStudents(viewer: Viewer, raw: string): Promise<SearchResult> {
  if (!can(viewer, "students.view")) return { ok: false, error: "students.search.noAccess" };
  const query = parseSearchQuery(raw);
  if (!query) return { ok: false, error: "students.search.typeSomething" };
  if (query.kind === "mobile" && !can(viewer, "students.contacts")) {
    return { ok: false, error: "students.search.noMobile" };
  }

  const db = adminClient();
  const scope = visibleBatchIds(viewer);
  if (scope && scope.length === 0) return { ok: true, query, hits: [], truncated: false };

  const matchedBy: SearchHit["matchedBy"] = query.kind === "id" ? "id" : query.kind;
  let ids: string[] | null = null;
  const earlierMatch = new Set<string>();

  if (query.kind === "id") {
    const { data } = await db.from("student_id_history").select("student_id, code, valid_to").eq("code", query.code);
    for (const r of (data ?? []) as { student_id: string; valid_to: string | null }[]) {
      if (r.valid_to) earlierMatch.add(r.student_id);
    }
    const { data: current } = await db.from("students").select("id").eq("code", query.code);
    ids = [...new Set([...((data ?? []) as { student_id: string }[]).map((r) => r.student_id), ...((current ?? []) as { id: string }[]).map((r) => r.id)])];
  } else if (query.kind === "mobile") {
    const { data } = await db.from("guardians").select("student_id").ilike("mobile", `%${query.digits}%`).limit(200);
    ids = [...new Set(((data ?? []) as { student_id: string }[]).map((r) => r.student_id))];
  }
  if (ids && ids.length === 0) return { ok: true, query, hits: [], truncated: false };

  let q = db.from("students").select(COLS).neq("status", "draft");
  if (ids) q = q.in("id", ids);
  if (query.kind === "name") q = q.ilike("name", `%${query.text.replace(/[%_]/g, "")}%`);
  if (query.kind === "class") {
    q = q.eq("current_class", query.cls).eq("status", "active");
    if (query.board) q = q.eq("board", query.board);
  }
  if (scope) q = q.in("batch_id", scope);
  const { data: rows } = await q.order("name").limit(LIMIT + 1);
  const students = (rows ?? []) as SearchHit["student"][];
  const truncated = students.length > LIMIT;
  const list = students.slice(0, LIMIT);

  const [{ data: history }, batches] = await Promise.all([
    list.length
      ? db.from("student_id_history").select("student_id, code").in("student_id", list.map((s) => s.id)).not("valid_to", "is", null)
      : Promise.resolve({ data: [] }),
    allBatches(true),
  ]);
  const earlier = new Map<string, string[]>();
  for (const h of (history ?? []) as { student_id: string; code: string }[]) {
    earlier.set(h.student_id, [...(earlier.get(h.student_id) ?? []), h.code]);
  }
  const bm = batchMap(batches);

  // Board, then class, then batch, then name.
  const hits = list
    .map((s) => {
      const b = s.batch_id ? bm.get(s.batch_id) : undefined;
      return {
        student: s,
        batch: b ? batchLabel(b) : null,
        earlierIds: (earlier.get(s.id) ?? []).filter((c) => c !== s.code),
        matchedBy: query.kind === "id" && earlierMatch.has(s.id) && s.code !== query.code ? ("earlier_id" as const) : matchedBy,
      };
    })
    .sort(
      (a, b) =>
        a.student.board.localeCompare(b.student.board) ||
        a.student.current_class - b.student.current_class ||
        (a.batch ?? "").localeCompare(b.batch ?? "") ||
        a.student.name.localeCompare(b.student.name),
    );
  return { ok: true, query, hits, truncated };
}
