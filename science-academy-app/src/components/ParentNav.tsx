"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, IndianRupee, MessagesSquare, Trophy } from "lucide-react";
import type { DictKey } from "@/lib/i18n";
import { useT } from "./I18nProvider";

const TABS: { href: string; label: DictKey; icon: typeof Trophy }[] = [
  { href: "/parent", label: "core.parentNav.group", icon: MessagesSquare },
  { href: "/parent/fees", label: "core.parentNav.fees", icon: IndianRupee },
  { href: "/parent/marks", label: "core.parentNav.marks", icon: Trophy },
  { href: "/parent/timetable", label: "core.parentNav.timetable", icon: CalendarDays },
];

/** Parent app bottom menu: Group, Fees, Marks, Timetable (bell is in the header). */
export function ParentNav() {
  const path = usePathname();
  const t = useT();
  return (
    <nav className="safe-bottom no-print fixed inset-x-0 bottom-0 z-20 border-t border-line bg-card/95 backdrop-blur">
      <ul className="mx-auto grid max-w-lg grid-cols-4">
        {TABS.map(({ href, label, icon: Icon }) => {
          const active = href === "/parent" ? path === "/parent" : path.startsWith(href);
          return (
            <li key={href}>
              <Link href={href} className={`flex flex-col items-center gap-1 pt-2 pb-1.5 text-[11px] font-semibold ${active ? "text-primary" : "text-faint"}`}>
                <Icon size={22} strokeWidth={active ? 2.3 : 1.8} />
                {t(label)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
