import Link from "next/link";
import { Bell, LogOut } from "lucide-react";
import { requireParent } from "@/lib/auth";
import { unreadCount } from "@/lib/notifications";
import { Logo } from "@/components/Logo";
import { ParentNav } from "@/components/ParentNav";
import { Footer } from "@/components/ui";

export default async function ParentLayout({ children }: { children: React.ReactNode }) {
  const viewer = await requireParent();
  const unread = await unreadCount(viewer.user.id);
  return (
    <div className="min-h-dvh pb-20">
      <header className="safe-top no-print sticky top-0 z-10 bg-navy text-white">
        <div className="mx-auto flex max-w-lg items-center gap-2 px-4 py-2.5">
          <div className="flex-1 rounded-full bg-white px-3 py-1">
            <Logo size={26} tagline={false} />
          </div>
          <Link href="/parent/notifications" className="relative grid h-10 w-10 place-items-center rounded-full hover:bg-white/10" aria-label={`Notifications, ${unread} new`}>
            <Bell size={21} />
            {unread > 0 && (
              <span className="absolute top-1 right-1 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-danger px-1 text-[10px] font-extrabold">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </Link>
          <form action="/api/auth/logout" method="post">
            <button className="grid h-10 w-10 place-items-center rounded-full hover:bg-white/10" aria-label="Log out" title="Log out">
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
