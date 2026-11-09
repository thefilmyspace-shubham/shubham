"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, LogOut } from "lucide-react";
import type { NavItem } from "@/lib/nav";
import { Logo } from "./Logo";
import { ICONS } from "./nav-icons";


function isActive(href: string, path: string) {
  if (href === "/") return path === "/";
  if (href === "/students") return path === "/students" || (path.startsWith("/students/") && path !== "/students/new");
  return path === href || path.startsWith(`${href}/`);
}

/** Desktop sidebar: every screen this person may open. */
export function Sidebar({
  items,
  user,
  unread,
}: {
  items: NavItem[];
  user: { name: string; staffId: string; roleLabel: string };
  unread: number;
}) {
  const path = usePathname();
  const main = items.filter((i) => i.section === "main");
  const admin = items.filter((i) => i.section === "admin");
  const link = (i: NavItem) => {
    const Icon = ICONS[i.icon];
    const active = isActive(i.href, path);
    return (
      <li key={i.href}>
        <Link
          href={i.href}
          className={`flex items-center gap-3 rounded-field px-3 py-2 text-[14px] font-semibold transition-colors ${
            active ? "bg-white/12 text-white" : "text-white/70 hover:bg-white/6 hover:text-white"
          }`}
        >
          <Icon size={18} strokeWidth={active ? 2.3 : 1.9} />
          {i.label}
        </Link>
      </li>
    );
  };
  return (
    <aside className="no-print fixed inset-y-0 left-0 z-20 hidden w-64 flex-col bg-navy text-white lg:flex">
      <div className="m-3 rounded-card bg-white px-3 py-2.5">
        <Logo size={34} />
      </div>
      <nav className="flex-1 overflow-y-auto px-3 pb-3">
        <ul className="space-y-0.5">{main.map(link)}</ul>
        {admin.length > 0 && (
          <>
            <p className="mt-5 mb-1.5 px-3 text-[11px] font-bold tracking-wider text-white/40 uppercase">Admin</p>
            <ul className="space-y-0.5">{admin.map(link)}</ul>
          </>
        )}
      </nav>
      <div className="border-t border-white/10 p-3">
        <Link
          href="/notifications"
          className={`mb-2 flex items-center gap-3 rounded-field px-3 py-2 text-[14px] font-semibold ${
            isActive("/notifications", path) ? "bg-white/12 text-white" : "text-white/70 hover:bg-white/6"
          }`}
        >
          <Bell size={18} />
          Notifications
          {unread > 0 && <span className="ml-auto rounded-full bg-danger px-1.5 text-[11px] font-extrabold">{unread > 99 ? "99+" : unread}</span>}
        </Link>
        <div className="flex items-center gap-2 px-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold">{user.name}</p>
            <p className="text-xs text-white/60">
              {user.staffId} · {user.roleLabel}
            </p>
          </div>
          <form action="/api/auth/logout" method="post">
            <button className="grid h-8 w-8 place-items-center rounded-full text-white/70 hover:bg-white/10" title="Log out" aria-label="Log out">
              <LogOut size={17} />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}

/** Phone bottom menu: the role's four main screens + More. */
export function BottomNav({ items }: { items: NavItem[] }) {
  const path = usePathname();
  if (/^\/(groups|assistant)\/./.test(path) || path === "/assistant") return null;
  const tabs = [...items, { href: "/more", label: "More", icon: "more" as const, anyOf: [], section: "main" as const }];
  const onMain = items.some((i) => isActive(i.href, path));
  return (
    <nav className="safe-bottom no-print fixed inset-x-0 bottom-0 z-20 border-t border-line bg-card/95 backdrop-blur lg:hidden">
      <ul className="mx-auto grid max-w-lg grid-cols-5">
        {tabs.map((i) => {
          const Icon = ICONS[i.icon];
          const active = i.href === "/more" ? !onMain : isActive(i.href, path);
          return (
            <li key={i.href}>
              <Link
                href={i.href}
                className={`flex flex-col items-center gap-1 pt-2 pb-1.5 text-[10.5px] font-semibold ${active ? "text-primary" : "text-faint"}`}
              >
                <Icon size={22} strokeWidth={active ? 2.3 : 1.8} />
                {i.label === "Timetable & tests" ? "Timetable" : i.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
