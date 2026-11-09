import Link from "next/link";
import { MessageCircleQuestion } from "lucide-react";
import { canSeeBatch, requirePermission } from "@/lib/auth";
import { getT } from "@/lib/i18n/server";
import { inbox } from "@/lib/queries";
import { dateTimeLabel } from "@/lib/format";
import { Card, Chip, Empty, FilterChips, Page, PageHeader } from "@/components/ui";

export const metadata = { title: "Parent queries" };

/** Staff inbox of parents' private questions (no AI; staff answer by hand). */
export default async function QueriesPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const viewer = await requirePermission("queries.reply");
  const { t } = await getT();
  const sp = await searchParams;
  const status = sp.status === "resolved" || sp.status === "all" ? sp.status : "open";
  const rows = (await inbox(viewer.user.id, status)).filter((r) => r.student && canSeeBatch(viewer, r.student.batch_id));
  return (
    <>
      <PageHeader title={t("groups.query.inboxTitle")} subtitle={t("groups.query.inboxSubtitle")} />
      <Page>
        <FilterChips
          items={(["open", "resolved", "all"] as const).map((s) => ({
            href: s === "open" ? "/queries" : `/queries?status=${s}`,
            label: t(s === "open" ? "groups.query.filterOpen" : s === "resolved" ? "groups.query.filterResolved" : "groups.query.filterAll"),
            active: status === s,
          }))}
        />
        <div className="mt-3">
          {rows.length === 0 ? (
            <Empty icon={MessageCircleQuestion}>{t("groups.query.noQueries")}</Empty>
          ) : (
            <Card className="divide-y divide-line overflow-hidden">
              {rows.map((r) => (
                <Link key={r.thread.id} href={`/queries/${r.thread.id}`} className="flex items-start gap-3 px-4 py-3 hover:bg-field">
                  <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${r.unread ? "bg-primary" : "bg-transparent"}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-bold text-navy">
                      {r.student?.name} <span className="font-semibold text-muted">· {r.student?.code}</span>
                    </p>
                    <p className="truncate text-xs text-muted">{t("groups.query.parentOf", { parent: r.parent?.name ?? "", student: r.student?.name ?? "" })}</p>
                    {r.last && <p className="mt-0.5 truncate text-[13.5px] text-fg/80">{r.last.body || `📎 ${r.last.attachment_name ?? ""}`}</p>}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span className="text-[11px] text-faint">{dateTimeLabel(r.thread.last_message_at)}</span>
                    {r.unread > 0 && <Chip tone="primary">{t("groups.query.newUnread", { n: r.unread })}</Chip>}
                    {r.thread.status === "resolved" ? (
                      <Chip tone="ok">{t("groups.query.resolved")}</Chip>
                    ) : r.thread.last_from === "parent" ? (
                      <Chip tone="warn">{t("groups.query.waiting")}</Chip>
                    ) : (
                      <Chip>{t("groups.query.answered")}</Chip>
                    )}
                  </div>
                </Link>
              ))}
            </Card>
          )}
        </div>
      </Page>
    </>
  );
}
