import { notFound } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { batchParentIds, groupFor, loadChat } from "@/lib/groups-db";
import { getT } from "@/lib/i18n/server";
import { ChatRoom } from "@/components/chat/ChatRoom";
import { PageHeader } from "@/components/ui";

export default async function GroupChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const viewer = await requireStaff();
  const { t } = await getT();
  const group = await groupFor(viewer, id);
  if (!group) notFound();
  const [messages, parents] = await Promise.all([
    loadChat(viewer, group),
    group.kind === "batch" && group.batch_id ? batchParentIds(group.batch_id) : Promise.resolve([]),
  ]);

  const subtitle =
    group.kind === "batch"
      ? t("groups.sub.batch", { n: parents.length })
      : group.kind === "management"
        ? t("groups.sub.management")
        : t("groups.sub.faculty");

  const composer = !group.canPost
    ? null
    : group.kind === "batch"
      ? { kind: "batch" as const, warning: t("groups.warn.batch") }
      : { kind: "staff" as const, warning: group.kind === "faculty" ? t("groups.hint.faculty") : t("groups.hint.management") };

  return (
    <>
      <PageHeader title={group.name} subtitle={subtitle} back="/groups" />
      <div className="mx-auto w-full max-w-4xl lg:px-8 lg:pt-2 lg:pb-6">
        <ChatRoom
          groupId={group.id}
          messages={messages}
          composer={composer}
          readOnlyText={group.kind === "batch" ? t("groups.readonly.batch") : t("groups.readonly.staff")}
        />
      </div>
    </>
  );
}
