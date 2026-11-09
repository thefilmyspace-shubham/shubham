import { notFound } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { batchParentIds, groupFor, loadChat } from "@/lib/groups-db";
import { BATCH_GROUP_WARNING, FACULTY_GROUP_HINT } from "@/lib/groups";
import { ChatRoom } from "@/components/chat/ChatRoom";
import { PageHeader } from "@/components/ui";

export default async function GroupChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const viewer = await requireStaff();
  const group = await groupFor(viewer, id);
  if (!group) notFound();
  const [messages, parents] = await Promise.all([
    loadChat(viewer, group),
    group.kind === "batch" && group.batch_id ? batchParentIds(group.batch_id) : Promise.resolve([]),
  ]);

  const subtitle =
    group.kind === "batch"
      ? `${parents.length} parent${parents.length === 1 ? "" : "s"} · only management and admin can post`
      : group.kind === "management"
        ? "Admin, Management and Reception"
        : "Admin, Management, Reception and all faculty";

  const composer = !group.canPost
    ? null
    : group.kind === "batch"
      ? { kind: "batch" as const, warning: BATCH_GROUP_WARNING }
      : { kind: "staff" as const, warning: group.kind === "faculty" ? FACULTY_GROUP_HINT : "Admin, Management and Reception can read this." };

  return (
    <>
      <PageHeader title={group.name} subtitle={subtitle} back="/groups" />
      <div className="mx-auto w-full max-w-4xl lg:px-8 lg:pt-2 lg:pb-6">
        <ChatRoom
          groupId={group.id}
          messages={messages}
          composer={composer}
          readOnlyText={group.kind === "batch" ? "Only management and admin can post in batch groups" : "Your login cannot write in this group"}
        />
      </div>
    </>
  );
}
