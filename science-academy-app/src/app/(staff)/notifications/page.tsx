import { requireStaff } from "@/lib/auth";
import { listNotifications } from "@/lib/notifications";
import { NotificationList } from "@/components/NotificationList";
import { Page, PageHeader } from "@/components/ui";

export const metadata = { title: "Notifications" };

export default async function NotificationsPage() {
  const viewer = await requireStaff();
  const items = await listNotifications(viewer.user.id);
  return (
    <>
      <PageHeader title="Notifications" back="/" />
      <Page>
        <NotificationList items={items} />
      </Page>
    </>
  );
}
