import { requireParent } from "@/lib/auth";
import { listNotifications } from "@/lib/notifications";
import { NotificationList } from "@/components/NotificationList";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Notifications" };

export default async function ParentNotifications() {
  const viewer = await requireParent();
  const [items, { t }] = await Promise.all([listNotifications(viewer.user.id), getT()]);
  return (
    <div className="mx-auto max-w-lg px-4 pt-4">
      <h1 className="mb-3 text-xl font-extrabold text-navy">{t("core.notifications")}</h1>
      <NotificationList items={items} />
    </div>
  );
}
