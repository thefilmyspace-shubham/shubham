import { requireStaff } from "@/lib/auth";
import { listNotifications } from "@/lib/notifications";
import { NotificationList } from "@/components/NotificationList";
import { Page, PageHeader } from "@/components/ui";
import { getT } from "@/lib/i18n/server";

export const metadata = { title: "Notifications" };

export default async function NotificationsPage() {
  const viewer = await requireStaff();
  const [items, { t }] = await Promise.all([listNotifications(viewer.user.id), getT()]);
  return (
    <>
      <PageHeader title={t("core.notifications")} back="/" />
      <Page>
        <NotificationList items={items} selectable />
      </Page>
    </>
  );
}
