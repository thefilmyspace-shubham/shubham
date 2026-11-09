import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight, SearchX } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { searchStudents } from "@/lib/search-db";
import { boardName } from "@/lib/ids";
import { HomeSearch } from "@/components/HomeSearch";
import { Card, Chip, Empty, Page, PageHeader } from "@/components/ui";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Search" };

/** Results of the Home search (the bar itself lives on Home). */
export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const viewer = await requireStaff();
  const { t } = await getT();
  if (!can(viewer, "students.view")) notFound();
  const result = q.trim() ? await searchStudents(viewer, q) : null;

  return (
    <>
      <PageHeader title={t("students.search.title")} subtitle={viewer.user.role === "faculty" ? t("students.search.yourBatches") : t("students.search.all")} back="/" />
      <Page>
        <HomeSearch defaultValue={q} showContacts={can(viewer, "students.contacts")} autoFocus={!q} />
        <div className="pt-4">
          {result && !result.ok && <Empty icon={SearchX}>{t(result.error)}</Empty>}
          {result?.ok && result.hits.length === 0 && <Empty icon={SearchX}>{t("students.search.none", { q })}</Empty>}
          {result?.ok && result.hits.length > 0 && (
            <>
              <p className="mb-2 text-xs font-semibold text-muted">
                {result.hits.length === 1
                  ? t("students.search.countOne", { by: t(`students.search.by.${result.hits[0].matchedBy}`) })
                  : t("students.search.count", {
                      n: `${result.hits.length}${result.truncated ? "+" : ""}`,
                      by: t(`students.search.by.${result.hits[0].matchedBy}`),
                    })}
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
                        {h.student.status !== "active" && <Chip tone="warn">{h.student.status === "left" ? t("students.left") : t("students.passedOut")}</Chip>}
                        {h.matchedBy === "earlier_id" && <Chip tone="violet">{t("students.search.earlierMatched")}</Chip>}
                        {h.matchedBy === "mobile" && <Chip tone="primary">{t("students.search.mobileMatched")}</Chip>}
                      </span>
                      <span className="block text-[12.5px] text-muted">
                        <span className="font-bold text-navy">{h.student.code}</span> · {boardName(h.student.board)} {h.student.current_class}
                        {h.batch ? ` · ${h.batch.replace(/^.*? \d+ · /, "")}` : ""}
                      </span>
                      {h.earlierIds.length > 0 && (
                        <span className="mt-1 flex flex-wrap gap-1">
                          {h.earlierIds.map((c) => (
                            <Chip key={c}>{t("students.search.earlierChip", { code: c })}</Chip>
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
