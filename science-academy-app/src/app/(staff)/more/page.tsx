import Link from "next/link";
import { Bell, ChevronRight, LogOut } from "lucide-react";
import { requireStaff } from "@/lib/auth";
import { navFor } from "@/lib/nav";
import { getT } from "@/lib/i18n/server";
import { LanguagePicker } from "@/components/LanguagePicker";
import { unreadCount } from "@/lib/notifications";
import { formatMobile } from "@/lib/ids";
import { ICONS } from "@/components/nav-icons";
import { Card, Page, PageHeader, Section } from "@/components/ui";

export const metadata = { title: "More" };

/** Phone menu: every screen this person may open. */
export default async function MorePage() {
  const viewer = await requireStaff();
  const items = navFor(viewer.perms).filter((i) => i.href !== "/");
  const [unread, { t }] = await Promise.all([unreadCount(viewer.user.id), getT()]);
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
      <PageHeader title={t("core.more.title")} />
      <Page>
        <Card className="flex items-center gap-3 p-4">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-navy text-lg font-extrabold text-white">{viewer.user.name.charAt(0)}</div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-bold">{viewer.user.name}</p>
            <p className="text-sm text-muted">
              {viewer.user.staff_id} · {t(`core.role.${viewer.user.role}`)} · {formatMobile(viewer.user.mobile)}
            </p>
          </div>
        </Card>
        <Section title={t("core.language")}>
          <Card className="p-4">
            <LanguagePicker />
            <p className="mt-2 text-xs text-muted">{t("core.more.languageHint")}</p>
          </Card>
        </Section>
        <Section title={t("core.more.screens")}>
          <Card className="divide-y divide-line overflow-hidden">
            {row("/notifications", t("core.notifications"), Bell, unread)}
            {items.filter((i) => i.section === "main").map((i) => row(i.href, t(i.label), ICONS[i.icon]))}
          </Card>
        </Section>
        {items.some((i) => i.section === "admin") && (
          <Section title={t("core.nav.adminSection")}>
            <Card className="divide-y divide-line overflow-hidden">
              {items.filter((i) => i.section === "admin").map((i) => row(i.href, t(i.label), ICONS[i.icon]))}
            </Card>
          </Section>
        )}
        <form action="/api/auth/logout" method="post" className="pt-5">
          <button className="btn btn-danger w-full">
            <LogOut size={17} /> {t("core.logout")}
          </button>
        </form>
      </Page>
    </>
  );
}
