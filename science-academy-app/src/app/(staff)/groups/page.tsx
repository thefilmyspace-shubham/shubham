import Link from "next/link";
import { notFound } from "next/navigation";
import { MessagesSquare, ShieldCheck, Users } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { groupSummaries, readableGroups } from "@/lib/groups-db";
import { MESSAGE_TYPE_LABEL } from "@/lib/groups";
import { dateTimeLabel } from "@/lib/format";
import { Card, Empty, Page, PageHeader, Section } from "@/components/ui";

export const metadata = { title: "Groups" };

export default async function GroupsPage() {
  const viewer = await requireStaff();
  if (!can(viewer, "groups.staff_chat") && !can(viewer, "groups.post_batch")) notFound();
  const groups = await readableGroups(viewer);
  const summaries = await groupSummaries(viewer, groups.map((g) => g.id));
  const staff = groups.filter((g) => g.kind !== "batch");
  const batch = groups.filter((g) => g.kind === "batch" && (g.batch?.active ?? true));

  const row = (g: (typeof groups)[number]) => {
    const s = summaries.get(g.id);
    const Icon = g.kind === "batch" ? Users : g.kind === "management" ? ShieldCheck : MessagesSquare;
    return (
      <Link key={g.id} href={`/groups/${g.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
        <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-full ${g.kind === "batch" ? "bg-green-soft text-ok" : "bg-navy-soft text-navy"}`}>
          <Icon size={20} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline gap-2">
            <span className="min-w-0 flex-1 truncate text-[15px] font-bold">{g.name}</span>
            {s?.last && <span className="shrink-0 text-[11px] text-faint">{dateTimeLabel(s.last.created_at)}</span>}
          </span>
          <span className="flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate text-[13px] text-muted">
              {s?.last
                ? `${s.last.senderName.split(" ")[0]}: ${s.last.type !== "chat" ? `[${MESSAGE_TYPE_LABEL[s.last.type]}] ` : ""}${s.last.body || s.last.attachment_name || "File"}`
                : g.kind === "batch"
                  ? "Parents of this batch · read only for them"
                  : "No messages yet"}
            </span>
            {s && s.unread > 0 && (
              <span className="grid h-5 min-w-5 place-items-center rounded-full bg-primary px-1.5 text-[11px] font-extrabold text-white">
                {s.unread > 99 ? "99+" : s.unread}
              </span>
            )}
          </span>
        </span>
      </Link>
    );
  };

  return (
    <>
      <PageHeader title="Groups" subtitle="Staff chat and batch groups for parents" />
      <Page>
        {groups.length === 0 && <Empty icon={MessagesSquare}>No groups for your login yet.</Empty>}
        {staff.length > 0 && (
          <Section title="Staff groups" className="pt-2">
            <Card className="divide-y divide-line overflow-hidden">{staff.map(row)}</Card>
          </Section>
        )}
        {batch.length > 0 && (
          <Section title="Batch groups (parents)">
            <p className="mb-2 text-xs text-muted">Only management and admin post here. Parents read. Never post fee details.</p>
            <Card className="divide-y divide-line overflow-hidden">{batch.map(row)}</Card>
          </Section>
        )}
      </Page>
    </>
  );
}
