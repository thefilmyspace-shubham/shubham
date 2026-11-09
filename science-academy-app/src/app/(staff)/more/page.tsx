import Link from "next/link";
import { Bell, ChevronRight, LogOut } from "lucide-react";
import { requireStaff } from "@/lib/auth";
import { navFor } from "@/lib/nav";
import { ROLE_LABEL } from "@/lib/permissions";
import { unreadCount } from "@/lib/notifications";
import { formatMobile } from "@/lib/ids";
import { ICONS } from "@/components/StaffNav";
import { Card, Page, PageHeader, Section } from "@/components/ui";

export const metadata = { title: "More" };

/** Phone menu: every screen this person may open. */
export default async function MorePage() {
  const viewer = await requireStaff();
  const items = navFor(viewer.perms).filter((i) => i.href !== "/");
  const unread = await unreadCount(viewer.user.id);
  const row = (href: string, label: string, Icon: typeof Bell, badge?: number) => (
    <Link key={href} href={href} className="flex items-center gap-3 px-4 py-3 hover:bg-field">
      <span className="grid h-9 w-9 place-items-center rounded-full bg-primary-soft text-primary">
        <Icon size={18} />
      </span>
      <span className="flex-1 text-[15px] font-semibold">{label}</span>
      {badge ? <span className="rounded-full bg-danger px-2 text-[11px] font-extrabold text-white">{badge}</span> : null}
      <ChevronRight size={18} className="text-faint" />
    </Link>
  );
  return (
    <>
      <PageHeader title="More" />
      <Page>
        <Card className="flex items-center gap-3 p-4">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-navy text-lg font-extrabold text-white">{viewer.user.name.charAt(0)}</div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-bold">{viewer.user.name}</p>
            <p className="text-sm text-muted">
              {viewer.user.staff_id} · {ROLE_LABEL[viewer.user.role]} · {formatMobile(viewer.user.mobile)}
            </p>
          </div>
        </Card>
        <Section title="Screens">
          <Card className="divide-y divide-line overflow-hidden">
            {row("/notifications", "Notifications", Bell, unread)}
            {items.filter((i) => i.section === "main").map((i) => row(i.href, i.label, ICONS[i.icon]))}
          </Card>
        </Section>
        {items.some((i) => i.section === "admin") && (
          <Section title="Admin">
            <Card className="divide-y divide-line overflow-hidden">
              {items.filter((i) => i.section === "admin").map((i) => row(i.href, i.label, ICONS[i.icon]))}
            </Card>
          </Section>
        )}
        <form action="/api/auth/logout" method="post" className="pt-5">
          <button className="btn btn-danger w-full">
            <LogOut size={17} /> Log out
          </button>
        </form>
      </Page>
    </>
  );
}
