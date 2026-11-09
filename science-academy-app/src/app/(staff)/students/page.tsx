import Link from "next/link";
import { ChevronRight, UserPlus, Users } from "lucide-react";
import { can, requirePermission, visibleBatchIds } from "@/lib/auth";
import { batchShort, batchesFor } from "@/lib/batches";
import { adminClient } from "@/lib/supabase/admin";
import { boardName, type Board } from "@/lib/ids";
import type { Batch, Student } from "@/lib/types";
import { Card, Chip, Empty, FilterChips, Page, PageHeader } from "@/components/ui";

export const metadata = { title: "Students" };

type Search = { board?: string; class?: string; batch?: string; status?: string };

const STATUS = [
  { key: "active", label: "Active" },
  { key: "draft", label: "Drafts" },
  { key: "left", label: "Left" },
  { key: "passed_out", label: "Passed out" },
] as const;

export default async function StudentsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const viewer = await requirePermission("students.view");
  const sp = await searchParams;
  const canEdit = can(viewer, "students.edit");
  const board = sp.board === "CB" || sp.board === "MP" ? (sp.board as Board) : null;
  const cls = sp.class && /^(6|7|8|9|10|11|12)$/.test(sp.class) ? Number(sp.class) : null;
  const statuses = STATUS.filter((s) => s.key !== "draft" || canEdit);
  const status = statuses.some((s) => s.key === sp.status) ? sp.status! : "active";

  const batches = await batchesFor(viewer);
  const batchById = new Map(batches.map((b) => [b.id, b]));
  const batch = sp.batch && batchById.has(sp.batch) ? sp.batch : null;
  const visible = visibleBatchIds(viewer);

  let q = adminClient().from("students").select("*").eq("status", status);
  if (board) q = q.eq("board", board);
  if (cls) q = q.eq("current_class", cls);
  if (batch) q = q.eq("batch_id", batch);
  if (visible) q = visible.length ? q.in("batch_id", visible) : q.eq("id", "00000000-0000-0000-0000-000000000000");
  const { data } = await q.order("name").limit(2000);
  const students = (data ?? []) as Student[];

  const href = (patch: Partial<Search>) => {
    const next = { board: board ?? undefined, class: cls ? String(cls) : undefined, batch: batch ?? undefined, status, ...patch };
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) if (v && !(k === "status" && v === "active")) params.set(k, v);
    const s = params.toString();
    return `/students${s ? `?${s}` : ""}`;
  };

  // Board → Class → Batch
  const tree = new Map<string, Map<number, Map<string, Student[]>>>();
  for (const s of students) {
    const byClass = tree.get(s.board) ?? new Map<number, Map<string, Student[]>>();
    tree.set(s.board, byClass);
    const byBatch = byClass.get(s.current_class) ?? new Map<string, Student[]>();
    byClass.set(s.current_class, byBatch);
    const key = s.batch_id ?? "none";
    byBatch.set(key, [...(byBatch.get(key) ?? []), s]);
  }
  const boards = [...tree.keys()].sort();
  const batchChoices = batches.filter((b) => (!board || b.board === board) && (!cls || b.class === cls));
  const label = (key: string): string => {
    const b: Batch | undefined = batchById.get(key);
    return b ? batchShort(b) : "No batch";
  };

  return (
    <>
      <PageHeader
        title="Students"
        subtitle={`${students.length} ${STATUS.find((s) => s.key === status)?.label.toLowerCase()} · Board, then class, then batch`}
        right={
          canEdit ? (
            <Link href="/students/new" className="btn btn-primary">
              <UserPlus size={16} /> <span className="hidden sm:inline">Register student</span>
            </Link>
          ) : undefined
        }
      />
      <Page wide>
        <div className="space-y-2">
          <FilterChips
            items={[
              { href: href({ board: undefined, batch: undefined }), label: "All boards", active: !board },
              { href: href({ board: "CB", batch: undefined }), label: "CBSE", active: board === "CB" },
              { href: href({ board: "MP", batch: undefined }), label: "MP Board", active: board === "MP" },
            ]}
          />
          <FilterChips
            items={[
              { href: href({ class: undefined, batch: undefined }), label: "All classes", active: !cls },
              ...[6, 7, 8, 9, 10, 11, 12].map((c) => ({ href: href({ class: String(c), batch: undefined }), label: `Class ${c}`, active: cls === c })),
            ]}
          />
          {batchChoices.length > 0 && (board || cls) && (
            <FilterChips
              items={[
                { href: href({ batch: undefined }), label: "All batches", active: !batch },
                ...batchChoices.map((b) => ({
                  href: href({ batch: b.id }),
                  label: `${board ? "" : `${b.board} `}${cls ? "" : `${b.class} · `}${batchShort(b)}`,
                  active: batch === b.id,
                })),
              ]}
            />
          )}
          <FilterChips items={statuses.map((s) => ({ href: href({ status: s.key }), label: s.label, active: status === s.key }))} />
        </div>

        {viewer.user.role === "faculty" && (
          <p className="mt-3 text-xs text-muted">You see students of your own batches only.</p>
        )}

        {!students.length ? (
          <div className="mt-5">
            <Empty icon={Users}>No students here.</Empty>
          </div>
        ) : (
          boards.map((b) => (
            <section key={b} className="mt-6">
              <h2 className="mb-2 text-lg font-extrabold text-navy">{boardName(b)}</h2>
              {[...tree.get(b)!.keys()]
                .sort((x, y) => x - y)
                .map((c) => {
                  const byBatch = tree.get(b)!.get(c)!;
                  const total = [...byBatch.values()].reduce((n, l) => n + l.length, 0);
                  return (
                    <div key={c} className="mb-4">
                      <h3 className="mb-2 text-sm font-bold text-muted">
                        Class {c} · {total} {total === 1 ? "student" : "students"}
                      </h3>
                      <div className="grid gap-3 lg:grid-cols-2">
                        {[...byBatch.keys()]
                          .sort((x, y) => label(x).localeCompare(label(y)))
                          .map((key) => (
                            <Card key={key} className="overflow-hidden">
                              <div className="flex items-center justify-between border-b border-line bg-navy-soft px-4 py-2">
                                <span className="text-[13px] font-bold text-navy">{label(key)}</span>
                                <span className="text-xs font-semibold text-muted">{byBatch.get(key)!.length}</span>
                              </div>
                              <ul className="divide-y divide-line">
                                {byBatch.get(key)!.map((s) => (
                                  <li key={s.id}>
                                    <Link
                                      href={s.status === "draft" ? `/students/${s.id}/edit` : `/students/${s.id}`}
                                      className="flex items-center gap-3 px-4 py-2.5 hover:bg-field"
                                    >
                                      <span className="min-w-0 flex-1">
                                        <span className="block truncate text-[14px] font-semibold">{s.name}</span>
                                        <span className="block truncate text-xs text-muted">{s.school ?? "School not entered"}</span>
                                      </span>
                                      {s.code ? (
                                        <span className="font-mono text-[12.5px] font-bold text-navy">{s.code}</span>
                                      ) : (
                                        <Chip tone="warn">Draft</Chip>
                                      )}
                                      <ChevronRight size={16} className="text-faint" />
                                    </Link>
                                  </li>
                                ))}
                              </ul>
                            </Card>
                          ))}
                      </div>
                    </div>
                  );
                })}
            </section>
          ))
        )}
      </Page>
    </>
  );
}
