import { Bell, CheckCheck } from "lucide-react";
import { markAllRead, openNotification } from "@/app/actions/notifications";
import { dateTimeLabel } from "@/lib/format";
import type { Notification } from "@/lib/types";
import { Card, Empty } from "./ui";

export function NotificationList({ items }: { items: Notification[] }) {
  if (!items.length) return <Empty icon={Bell}>No notifications yet.</Empty>;
  const unread = items.filter((n) => !n.read_at).length;
  return (
    <div className="space-y-3">
      {unread > 0 && (
        <form action={markAllRead} className="flex justify-end">
          <button className="btn btn-ghost py-1.5 text-[13px]">
            <CheckCheck size={15} /> Mark all read ({unread})
          </button>
        </form>
      )}
      <Card className="divide-y divide-line overflow-hidden">
        {items.map((n) => (
          <form key={n.id} action={openNotification}>
            <input type="hidden" name="id" value={n.id} />
            <button className={`flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-field ${n.read_at ? "" : "bg-primary-soft/40"}`}>
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read_at ? "bg-transparent" : "bg-primary"}`} />
              <span className="min-w-0 flex-1">
                <span className="block text-[14px] font-bold text-fg">{n.title}</span>
                {n.body && <span className="block text-[13px] text-muted">{n.body}</span>}
                <span className="mt-0.5 block text-[11.5px] text-faint">{dateTimeLabel(n.created_at)}</span>
              </span>
            </button>
          </form>
        ))}
      </Card>
    </div>
  );
}
