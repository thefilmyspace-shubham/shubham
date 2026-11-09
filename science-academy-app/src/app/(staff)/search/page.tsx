import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight, SearchX } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { searchStudents } from "@/lib/search-db";
import { boardName } from "@/lib/ids";
import { HomeSearch } from "@/components/HomeSearch";
import { Card, Chip, Empty, Page, PageHeader } from "@/components/ui";

export const metadata = { title: "Search" };

const MATCHED: Record<string, string> = {
  id: "ID",
  earlier_id: "Earlier ID",
  name: "Name",
  mobile: "Parent's mobile",
  class: "Class",
};

/** Results of the Home search (the bar itself lives on Home). */
export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const viewer = await requireStaff();
  if (!can(viewer, "students.view")) notFound();
  const result = q.trim() ? await searchStudents(viewer, q) : null;

  return (
    <>
      <PageHeader title="Search" subtitle={viewer.user.role === "faculty" ? "Students of your batches" : "All students"} back="/" />
      <Page>
        <HomeSearch defaultValue={q} showContacts={can(viewer, "students.contacts")} autoFocus={!q} />
        <div className="pt-4">
          {result && !result.ok && <Empty icon={SearchX}>{result.error}</Empty>}
          {result?.ok && result.hits.length === 0 && <Empty icon={SearchX}>No student found for “{q}”.</Empty>}
          {result?.ok && result.hits.length > 0 && (
            <>
              <p className="mb-2 text-xs font-semibold text-muted">
                {result.hits.length}
                {result.truncated ? "+" : ""} student{result.hits.length === 1 ? "" : "s"} · matched by {MATCHED[result.hits[0].matchedBy].toLowerCase()}
              </p>
              <Card className="divide-y divide-line overflow-hidden">
                {result.hits.map((h) => (
                  <Link key={h.student.id} href={`/students/${h.student.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-navy-soft text-[15px] font-extrabold text-navy">
                      {h.student.name.charAt(0)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[15px] font-bold">{h.student.name}</span>
                        {h.student.status !== "active" && <Chip tone="warn">{h.student.status === "left" ? "Left" : "Passed out"}</Chip>}
                        {h.matchedBy === "earlier_id" && <Chip tone="violet">Earlier ID matched</Chip>}
                        {h.matchedBy === "mobile" && <Chip tone="primary">Parent&apos;s mobile matched</Chip>}
                      </span>
                      <span className="block text-[12.5px] text-muted">
                        <span className="font-bold text-navy">{h.student.code}</span> · {boardName(h.student.board)} {h.student.current_class}
                        {h.batch ? ` · ${h.batch.replace(/^.*? \d+ · /, "")}` : ""}
                      </span>
                      {h.earlierIds.length > 0 && (
                        <span className="mt-1 flex flex-wrap gap-1">
                          {h.earlierIds.map((c) => (
                            <Chip key={c}>Earlier ID {c}</Chip>
                          ))}
                        </span>
                      )}
                    </span>
                    <ChevronRight size={18} className="shrink-0 text-faint" />
                  </Link>
                ))}
              </Card>
            </>
          )}
        </div>
      </Page>
    </>
  );
}
