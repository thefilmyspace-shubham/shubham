import { SubmitButton } from "@/components/SubmitButton";
import { Bell, CheckCheck } from "lucide-react";
import {
  deleteNotifications,
  markAllRead,
  openNotification,
} from "@/app/actions/notifications";
import { BulkBar, BulkCheck } from "./BulkBar";
import { dateTimeLabel } from "@/lib/format";
import type { Notification } from "@/lib/types";
import { getT } from "@/lib/i18n/server";
import { Card, Empty } from "./ui";

export async function NotificationList({ items }: { items: Notification[] }) {
  const { t } = await getT();
  if (!items.length) return <Empty icon={Bell}>{t("core.notif.empty")}</Empty>;
  const unread = items.filter((n) => !n.read_at).length;
  return (
    <div className="space-y-3">
      {unread > 0 && (
        <form action={markAllRead} className="flex justify-end">
          <SubmitButton className="btn btn-ghost py-1.5 text-[13px]">
            <CheckCheck size={15} /> {t("core.notif.markAll", { n: unread })}
          </SubmitButton>
        </form>
      )}
      <Card className="divide-y divide-line overflow-hidden">
        {items.map((n) => (
          <div
            key={n.id}
            className={`flex items-start ${n.read_at ? "" : "bg-primary-soft/40"}`}
          >
            <label
              className="cursor-pointer py-3 pr-1 pl-4"
              title={t("core.notif.select")}
            >
              <BulkCheck
                group="notifications"
                id={n.id}
                label={t("core.notif.select")}
              />
            </label>
            <form action={openNotification} className="min-w-0 flex-1">
              <input type="hidden" name="id" value={n.id} />
              <button className="flex w-full items-start gap-3 py-3 pr-4 pl-2 text-left hover:bg-field">
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read_at ? "bg-transparent" : "bg-primary"}`}
                />
                <span className="min-w-0 flex-1">
                  <span className="block text-[14px] font-bold text-fg">
                    {n.title}
                  </span>
                  {n.body && (
                    <span className="block text-[13px] text-muted">
                      {n.body}
                    </span>
                  )}
                  <span className="mt-0.5 block text-[11.5px] text-faint">
                    {dateTimeLabel(n.created_at)}
                  </span>
                </span>
              </button>
            </form>
          </div>
        ))}
      </Card>
      <BulkBar group="notifications" action={deleteNotifications} />
    </div>
  );
}
