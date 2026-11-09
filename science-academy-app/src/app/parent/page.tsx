import { Lock, MessagesSquare } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { adminClient } from "@/lib/supabase/admin";
import { groupFor, loadChat } from "@/lib/groups-db";
import { ChildStrip } from "@/components/ChildStrip";
import { ChatRoom } from "@/components/chat/ChatRoom";
import { Empty } from "@/components/ui";

export const metadata = { title: "Group" };

/** Parent app, Group tab: read-only posts of the child's batch group. */
export default async function ParentGroupPage({ searchParams }: { searchParams: Promise<{ child?: string }> }) {
  const { child: childParam } = await searchParams;
  const { viewer, children, child } = await parentContext(childParam);
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty icon={MessagesSquare}>No student is linked to this number yet. Please contact the academy.</Empty>
      </div>
    );
  }

  const { data: row } = child.batch_id
    ? await adminClient().from("groups").select("id").eq("batch_id", child.batch_id).maybeSingle<{ id: string }>()
    : { data: null };
  const group = row ? await groupFor(viewer, row.id) : null;
  const messages = group ? await loadChat(viewer, group, 150) : [];

  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent" />
      <div className="sticky top-[60px] z-[5] border-b border-line bg-card">
        <div className="mx-auto flex max-w-lg items-center gap-2 px-4 py-2 text-[12.5px] font-semibold text-muted">
          <Lock size={13} className="shrink-0" />
          <span className="min-w-0 flex-1 truncate">{group ? group.name : "Batch group"}</span>
          <span className="shrink-0">Only management and admin can post here</span>
        </div>
      </div>
      <div className="mx-auto max-w-lg">
        {group ? (
          <ChatRoom groupId={group.id} messages={messages} composer={null} bottomBar={false} showSenderTag={false} />
        ) : (
          <div className="px-4 pt-6">
            <Empty icon={MessagesSquare}>{child.name} is not in a batch yet, so there are no batch posts.</Empty>
          </div>
        )}
      </div>
    </>
  );
}
