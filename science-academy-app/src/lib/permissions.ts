// The permissions engine (spec §5, §6).
//
// Each key has a default per role. Admin can change a key for a whole role
// (role_permissions) or for one person (user_permissions). A person's own
// setting wins over their role's, which wins over the default.
// Some keys are locked: Admin-only master controls, and everything for Admin
// (so the owner can never lock themselves out).

export type Role = "admin" | "management" | "reception" | "faculty" | "parent";
export const STAFF_ROLES: Exclude<Role, "parent">[] = ["admin", "management", "reception", "faculty"];
export const ROLES: Role[] = [...STAFF_ROLES, "parent"];

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Admin",
  management: "Management",
  reception: "Reception",
  faculty: "Faculty",
  parent: "Parent",
};

export const ROLE_PREFIX: Record<Exclude<Role, "parent">, string> = {
  admin: "AD",
  management: "MG",
  reception: "RC",
  faculty: "FC",
};

type Def = {
  label: string;
  /** Shown under the label in the Access control matrix. */
  hint?: string;
  defaults: Record<Exclude<Role, "parent">, boolean>;
  /** What a parent gets (fixed: always their own child only). */
  parent: string;
  /** Admin-only master control; cannot be given to anyone else. */
  adminOnly?: boolean;
};

const d = (admin: boolean, management: boolean, reception: boolean, faculty: boolean) => ({
  admin,
  management,
  reception,
  faculty,
});

export const PERMISSIONS = {
  "students.view": {
    label: "See student profile, attendance, test scores",
    hint: "Faculty: own batches only",
    defaults: d(true, true, true, true),
    parent: "Own child",
  },
  "students.contacts": {
    label: "See parents' phone numbers",
    hint: "Reception: only in the call log, for students with fees due",
    defaults: d(true, true, false, false),
    parent: "No",
  },
  "students.marksheets": {
    label: "See marksheets",
    defaults: d(true, true, true, true),
    parent: "Own child",
  },
  "students.edit": {
    label: "Register or edit students",
    defaults: d(true, true, true, false),
    parent: "No",
  },
  "fees.view": {
    label: "See fees and the call log",
    defaults: d(true, false, true, false),
    parent: "Own child (status, receipts)",
  },
  "bills.create": {
    label: "Make bills and print",
    defaults: d(true, false, true, false),
    parent: "No",
  },
  "bills.cancel": {
    label: "Cancel a bill (reason needed)",
    defaults: d(true, false, false, false),
    parent: "No",
  },
  "attendance.mark": {
    label: "Mark attendance",
    hint: "Faculty: own batches",
    defaults: d(true, false, false, true),
    parent: "No",
  },
  "attendance.correct": {
    label: "Correct attendance after 24 hours",
    hint: "Every correction is logged",
    defaults: d(true, true, false, false),
    parent: "No",
  },
  "academics.edit": {
    label: "Edit timetable and tests",
    defaults: d(true, true, false, false),
    parent: "No",
  },
  "marks.enter": {
    label: "Enter marks",
    hint: "Faculty: own batches",
    defaults: d(true, true, false, true),
    parent: "No",
  },
  "ranks.view": {
    label: "See ranks, download reports",
    hint: "Faculty: own batches",
    defaults: d(true, true, true, true),
    parent: "No",
  },
  "ranks.all_batches": {
    label: "See ranks of all batches",
    hint: "Off: only own batches",
    defaults: d(true, true, true, false),
    parent: "No",
  },
  "groups.post_batch": {
    label: "Post in batch groups (parents)",
    defaults: d(true, true, false, false),
    parent: "No (read only)",
  },
  "groups.staff_chat": {
    label: "Chat in staff groups",
    defaults: d(true, true, true, true),
    parent: "No",
  },
  "queries.reply": {
    label: "Answer parent queries",
    defaults: d(true, true, true, false),
    parent: "Own child",
  },
  "ai.ask": {
    label: "Ask the AI assistant",
    defaults: d(true, true, true, false),
    parent: "No",
  },
  "ai.act": {
    label: "Let the AI take actions",
    defaults: d(true, false, false, false),
    parent: "No",
    adminOnly: true,
  },
  "admin.promotion": {
    label: "Year-end promotion",
    defaults: d(true, false, false, false),
    parent: "No",
    adminOnly: true,
  },
  "admin.access": {
    label: "Access control",
    defaults: d(true, false, false, false),
    parent: "No",
    adminOnly: true,
  },
  "admin.activity": {
    label: "Activity log",
    defaults: d(true, false, false, false),
    parent: "No",
    adminOnly: true,
  },
  "admin.backup": {
    label: "Backup and exports",
    defaults: d(true, false, false, false),
    parent: "No",
    adminOnly: true,
  },
} satisfies Record<string, Def>;

export type PermissionKey = keyof typeof PERMISSIONS;
export const PERMISSION_KEYS = Object.keys(PERMISSIONS) as PermissionKey[];

export function isPermissionKey(key: string): key is PermissionKey {
  return key in PERMISSIONS;
}

/** Locked cells in the matrix: Admin's column, and Admin-only master controls. */
export function isLocked(role: Role, key: PermissionKey): boolean {
  if (role === "admin" || role === "parent") return true;
  return Boolean((PERMISSIONS[key] as Def).adminOnly);
}

export type Overrides = Partial<Record<PermissionKey, boolean>>;

export function roleDefault(role: Role, key: PermissionKey): boolean {
  if (role === "parent") return false;
  return PERMISSIONS[key].defaults[role];
}

/** A role's value: its saved setting, else the default. Locked cells always use the default. */
export function roleValue(role: Role, key: PermissionKey, roleOverrides: Overrides): boolean {
  if (isLocked(role, key)) return roleDefault(role, key);
  return roleOverrides[key] ?? roleDefault(role, key);
}

/** One person's final permissions: own setting > role setting > default. */
export function resolvePermissions(role: Role, roleOverrides: Overrides, userOverrides: Overrides): Record<PermissionKey, boolean> {
  const out = {} as Record<PermissionKey, boolean>;
  for (const key of PERMISSION_KEYS) {
    out[key] = isLocked(role, key) ? roleDefault(role, key) : (userOverrides[key] ?? roleValue(role, key, roleOverrides));
  }
  return out;
}

/** "1 extra: sees ranks of all batches" / "2 removed" for the people list. */
export function overrideSummary(role: Role, roleOverrides: Overrides, userOverrides: Overrides): string | null {
  const extra: string[] = [];
  const removed: string[] = [];
  for (const key of PERMISSION_KEYS) {
    const mine = userOverrides[key];
    if (mine === undefined || isLocked(role, key)) continue;
    const base = roleValue(role, key, roleOverrides);
    if (mine && !base) extra.push(PERMISSIONS[key].label);
    if (!mine && base) removed.push(PERMISSIONS[key].label);
  }
  const parts: string[] = [];
  if (extra.length) parts.push(`${extra.length} extra: ${extra.map(lower).join(", ")}`);
  if (removed.length) parts.push(`${removed.length} removed: ${removed.map(lower).join(", ")}`);
  return parts.length ? parts.join(" · ") : null;
}

function lower(s: string): string {
  return s.charAt(0).toLowerCase() + s.slice(1);
}
