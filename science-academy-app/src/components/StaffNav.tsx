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
            active ? "bg-primary-soft text-primary" : "text-fg/75 hover:bg-field hover:text-navy"
          }`}
        >
          <Icon size={18} strokeWidth={active ? 2.3 : 1.9} />
          {i.label}
        </Link>
      </li>
    );
  };
  return (
    <aside className="no-print fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-line bg-card text-fg lg:flex">
      <div className="px-4 pt-5 pb-4">
        <Logo size={50} />
      </div>
      <div className="mx-4 mb-3 h-1 rounded-full bg-gradient-to-r from-navy via-primary to-green" />
      <nav className="flex-1 overflow-y-auto px-3 pb-3">
        <ul className="space-y-0.5">{main.map(link)}</ul>
        {admin.length > 0 && (
          <>
            <p className="mt-5 mb-1.5 px-3 text-[11px] font-bold tracking-wider text-faint uppercase">Admin</p>
            <ul className="space-y-0.5">{admin.map(link)}</ul>
          </>
        )}
      </nav>
      <div className="border-t border-line p-3">
        <Link
          href="/notifications"
          className={`mb-2 flex items-center gap-3 rounded-field px-3 py-2 text-[14px] font-semibold ${
            isActive("/notifications", path) ? "bg-primary-soft text-primary" : "text-fg/75 hover:bg-field"
          }`}
        >
          <Bell size={18} />
          Notifications
          {unread > 0 && <span className="ml-auto rounded-full bg-danger px-1.5 text-[11px] font-extrabold text-white">{unread > 99 ? "99+" : unread}</span>}
        </Link>
        <div className="flex items-center gap-2 rounded-field bg-field px-3 py-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-navy">{user.name}</p>
            <p className="text-xs text-muted">
              {user.staffId} · {user.roleLabel}
            </p>
          </div>
          <form action="/api/auth/logout" method="post">
            <button className="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-card hover:text-danger" title="Log out" aria-label="Log out">
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
