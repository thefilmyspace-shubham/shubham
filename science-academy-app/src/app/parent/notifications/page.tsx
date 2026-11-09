import { requireParent } from "@/lib/auth";
import { listNotifications } from "@/lib/notifications";
import { NotificationList } from "@/components/NotificationList";

export const metadata = { title: "Notifications" };

export default async function ParentNotifications() {
  const viewer = await requireParent();
  const items = await listNotifications(viewer.user.id);
  return (
    <div className="mx-auto max-w-lg px-4 pt-4">
      <h1 className="mb-3 text-xl font-extrabold text-navy">Notifications</h1>
      <NotificationList items={items} />
    </div>
  );
}
