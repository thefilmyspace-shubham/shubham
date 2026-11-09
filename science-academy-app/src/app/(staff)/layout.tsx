import { requireStaff } from "@/lib/auth";
import { bottomNavFor, navFor } from "@/lib/nav";
import { getT } from "@/lib/i18n/server";
import { unreadCount } from "@/lib/notifications";
import { BottomNav, Sidebar } from "@/components/StaffNav";
import { Footer } from "@/components/ui";

export default async function StaffLayout({ children }: { children: React.ReactNode }) {
  const viewer = await requireStaff();
  const role = viewer.user.role as Exclude<typeof viewer.user.role, "parent">;
  const [unread, { t }] = await Promise.all([unreadCount(viewer.user.id), getT()]);
  return (
    <div className="min-h-dvh">
      <Sidebar
        items={navFor(viewer.perms)}
        user={{ name: viewer.user.name, staffId: viewer.user.staff_id, roleLabel: t(`core.role.${role}`) }}
        unread={unread}
      />
      <div className="flex min-h-dvh flex-col pb-20 lg:pb-0 lg:pl-64">
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
      <BottomNav items={bottomNavFor(role, viewer.perms)} />
    </div>
  );
}
