// Every staff screen, who may open it, and each role's phone bottom menu.
// Icons are named here and mapped to lucide icons in the nav components.

import type { PermissionKey, Role } from "./permissions";

export type NavIcon =
  | "home"
  | "students"
  | "register"
  | "fees"
  | "calls"
  | "billing"
  | "attendance"
  | "timetable"
  | "ranks"
  | "groups"
  | "assistant"
  | "access"
  | "batches"
  | "activity"
  | "promotion"
  | "backup"
  | "bell"
  | "more";

export type NavItem = {
  href: string;
  label: string;
  icon: NavIcon;
  /** Any one of these opens it. Empty = every staff member. */
  anyOf: PermissionKey[];
  section: "main" | "admin";
};

export const NAV: NavItem[] = [
  { href: "/", label: "Home", icon: "home", anyOf: [], section: "main" },
  { href: "/students", label: "Students", icon: "students", anyOf: ["students.view"], section: "main" },
  { href: "/students/new", label: "Register student", icon: "register", anyOf: ["students.edit"], section: "main" },
  { href: "/fees", label: "Fees", icon: "fees", anyOf: ["fees.view"], section: "main" },
  { href: "/calls", label: "Call log", icon: "calls", anyOf: ["fees.view"], section: "main" },
  { href: "/billing", label: "Billing", icon: "billing", anyOf: ["bills.create"], section: "main" },
  { href: "/attendance", label: "Attendance", icon: "attendance", anyOf: ["attendance.mark", "students.view"], section: "main" },
  { href: "/timetable", label: "Timetable & tests", icon: "timetable", anyOf: [], section: "main" },
  { href: "/ranks", label: "Ranks", icon: "ranks", anyOf: ["ranks.view"], section: "main" },
  { href: "/groups", label: "Groups", icon: "groups", anyOf: ["groups.staff_chat", "groups.post_batch"], section: "main" },
  { href: "/assistant", label: "AI assistant", icon: "assistant", anyOf: ["ai.ask"], section: "main" },
  { href: "/admin/access", label: "Access control", icon: "access", anyOf: ["admin.access"], section: "admin" },
  { href: "/admin/batches", label: "Batches & faculty", icon: "batches", anyOf: ["admin.access"], section: "admin" },
  { href: "/admin/activity", label: "Activity log", icon: "activity", anyOf: ["admin.activity"], section: "admin" },
  { href: "/admin/promotion", label: "Year-end promotion", icon: "promotion", anyOf: ["admin.promotion"], section: "admin" },
  { href: "/admin/backup", label: "Backup", icon: "backup", anyOf: ["admin.backup"], section: "admin" },
];

const BOTTOM: Record<Exclude<Role, "parent">, string[]> = {
  admin: ["/", "/students", "/fees", "/groups"],
  management: ["/", "/students", "/attendance", "/groups"],
  reception: ["/", "/calls", "/billing", "/students"],
  faculty: ["/", "/attendance", "/timetable", "/groups"],
};

export function allowed(item: NavItem, perms: Record<PermissionKey, boolean>): boolean {
  return item.anyOf.length === 0 || item.anyOf.some((k) => perms[k]);
}

export function navFor(perms: Record<PermissionKey, boolean>): NavItem[] {
  return NAV.filter((i) => allowed(i, perms));
}

/** Four tabs + More. A tab the person cannot open is replaced by the next screen they can. */
export function bottomNavFor(role: Exclude<Role, "parent">, perms: Record<PermissionKey, boolean>): NavItem[] {
  const mine = navFor(perms).filter((i) => i.href !== "/students/new");
  const wanted = BOTTOM[role].map((href) => mine.find((i) => i.href === href)).filter((i): i is NavItem => Boolean(i));
  for (const item of mine) {
    if (wanted.length >= 4) break;
    if (!wanted.includes(item)) wanted.push(item);
  }
  return wanted.slice(0, 4);
}
