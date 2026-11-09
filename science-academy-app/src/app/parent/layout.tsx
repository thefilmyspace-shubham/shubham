import Link from "next/link";
import { Bell, Languages, LogOut } from "lucide-react";
import { getT } from "@/lib/i18n/server";
import { requireParent } from "@/lib/auth";
import { unreadCount } from "@/lib/notifications";
import { Logo } from "@/components/Logo";
import { ParentNav } from "@/components/ParentNav";
import { Footer } from "@/components/ui";

export default async function ParentLayout({ children }: { children: React.ReactNode }) {
  const viewer = await requireParent();
  const [unread, { t }] = await Promise.all([unreadCount(viewer.user.id), getT()]);
  return (
    <div className="min-h-dvh pb-20">
      <header className="safe-top no-print sticky top-0 z-10 border-b border-line bg-card text-navy">
        <div className="mx-auto flex max-w-lg items-center gap-2 px-4 py-2.5">
          <div className="flex flex-1 items-center">
            <Logo size={34} />
          </div>
          <Link href="/parent/notifications" className="relative grid h-10 w-10 place-items-center rounded-full hover:bg-field" aria-label={t("core.parent.notificationsAria", { n: unread })}>
            <Bell size={21} />
            {unread > 0 && (
              <span className="absolute top-1 right-1 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-danger px-1 text-[10px] font-extrabold text-white">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </Link>
          <Link href="/parent/language" className="grid h-10 w-10 place-items-center rounded-full text-muted hover:bg-field hover:text-primary" aria-label={t("core.language")} title={t("core.language")}>
            <Languages size={20} />
          </Link>
          <form action="/api/auth/logout" method="post">
            <button className="grid h-10 w-10 place-items-center rounded-full text-muted hover:bg-field hover:text-danger" aria-label={t("core.logout")} title={t("core.logout")}>
              <LogOut size={19} />
            </button>
          </form>
        </div>
      </header>
      <main>{children}</main>
      <Footer />
      <ParentNav />
    </div>
  );
}
