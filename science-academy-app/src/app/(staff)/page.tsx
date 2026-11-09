import Link from "next/link";
import { Bell } from "lucide-react";
import { can, requireStaff } from "@/lib/auth";
import { unreadCount } from "@/lib/notifications";
import { dayLabel, todayIst } from "@/lib/format";
import { toIst } from "@/lib/ids";
import { HomeSearch } from "@/components/HomeSearch";
import { LogoMark } from "@/components/Logo";
import { Page } from "@/components/ui";
import { AdminHome, FacultyHome, ManagementHome, ReceptionHome } from "./_home/homes";
import { getT } from "@/lib/i18n/server";
import type { TFn } from "@/lib/i18n";

export async function generateMetadata() {
  const { t } = await getT();
  return { title: t("admin.home.title") };
}

function greeting(t: TFn): string {
  const h = toIst(new Date()).getUTCHours();
  return h < 12 ? t("admin.home.morning") : h < 17 ? t("admin.home.afternoon") : t("admin.home.evening");
}

/** Home: the one search bar, the bell, and the role's dashboard. */
export default async function HomePage() {
  const viewer = await requireStaff();
  const { t } = await getT();
  const unread = await unreadCount(viewer.user.id);
  const role = viewer.user.role;
  return (
    <>
      <header className="safe-top no-print sticky top-0 z-10 bg-card/95 shadow-bar backdrop-blur lg:static lg:bg-transparent lg:shadow-none">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-2.5 lg:px-8 lg:pt-7">
          <span className="lg:hidden">
            <LogoMark size={34} />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[20px] font-extrabold tracking-tight text-navy lg:text-[28px]">
              {greeting(t)}, {viewer.user.name.split(" ")[0]}
            </h1>
            <p className="truncate text-xs text-muted lg:text-sm">
              {dayLabel(todayIst())} · {viewer.user.staff_id} · {t(`core.role.${role}`)}
            </p>
          </div>
          <Link
            href="/notifications"
            className="relative grid h-11 w-11 shrink-0 place-items-center rounded-full bg-card text-navy shadow-card hover:bg-field"
            aria-label={t("admin.home.bellLabel", { n: unread })}
          >
            <Bell size={21} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 grid h-[19px] min-w-[19px] place-items-center rounded-full bg-danger px-1 text-[10.5px] font-extrabold text-white">
                {unread > 99 ? "99+" : unread}
              </span>
            )}
          </Link>
        </div>
      </header>
      <Page wide>
        {can(viewer, "students.view") && <HomeSearch showContacts={can(viewer, "students.contacts")} />}
        {role === "admin" && <AdminHome viewer={viewer} />}
        {role === "reception" && <ReceptionHome viewer={viewer} />}
        {role === "management" && <ManagementHome viewer={viewer} />}
        {role === "faculty" && <FacultyHome viewer={viewer} />}
      </Page>
    </>
  );
}
