import { MessageCircleQuestion } from "lucide-react";
import { parentContext } from "@/lib/parent";
import { getT } from "@/lib/i18n/server";
import { threadMessages, threadOf } from "@/lib/queries";
import { ChildStrip } from "@/components/ChildStrip";
import { Empty } from "@/components/ui";
import { QueryChat } from "@/components/query/QueryChat";

export const metadata = { title: "Query" };

/** The parent's private chat with the academy about this child (answered by staff, no AI). */
export default async function ParentQueryPage() {
  const { t } = await getT();
  const { viewer, children, child } = await parentContext();
  if (!child) {
    return (
      <div className="mx-auto max-w-lg px-4 pt-6">
        <Empty icon={MessageCircleQuestion}>{t("academics.noStudentLinked")}</Empty>
      </div>
    );
  }
  const thread = await threadOf(viewer.user.id, child.id).catch(() => null);
  const lines = thread ? await threadMessages(thread.id) : [];
  return (
    <>
      <ChildStrip list={children} current={child} basePath="/parent/query" />
      <div className="mx-auto max-w-lg">
        <div className="px-4 pt-3 pb-2">
          <h1 className="text-xl font-extrabold text-navy">{t("groups.query.title")}</h1>
          <p className="text-[13px] text-muted">{t("groups.query.subtitle")}</p>
          {thread?.status === "resolved" && <p className="mt-1 text-[12.5px] font-semibold text-ok">{t("groups.query.resolvedNote")}</p>}
        </div>
        <QueryChat
          mode="parent"
          studentId={child.id}
          threadId={thread?.id ?? null}
          lines={lines.map((m) => ({
            id: m.id,
            mine: m.sender_id === viewer.user.id,
            from: m.senderRole === "parent" ? m.senderName : `${t("groups.query.academy")} · ${m.senderName}`,
            body: m.body,
            attachment: m.attachment_name,
            createdAt: m.created_at,
          }))}
        />
      </div>
    </>
  );
}
