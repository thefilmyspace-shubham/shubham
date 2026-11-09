import { LogOut, ShieldCheck, UserCheck, UserX } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { formatMobile } from "@/lib/ids";
import {
  isLocked,
  overrideSummary,
  PERMISSION_KEYS,
  PERMISSIONS,
  ROLE_LABEL,
  roleDefault,
  roleValue,
  STAFF_ROLES,
  type Overrides,
  type PermissionKey,
  type Role,
} from "@/lib/permissions";
import type { AppUser } from "@/lib/types";
import { Banner, Card, Chip, Page, PageHeader, Section } from "@/components/ui";
import { Matrix, type MatrixRow } from "./Matrix";
import { AddStaff } from "./AddStaff";
import { logoutEverywhere, savePersonAccess, setSuspended } from "./actions";

export const metadata = { title: "Access control" };

export default async function AccessPage({ searchParams }: { searchParams: Promise<{ role?: string }> }) {
  const viewer = await requirePermission("admin.access");
  const { role: roleFilter } = await searchParams;
  const db = adminClient();
  const [{ data: roleRows }, { data: userRows }, { data: people }, { data: sessions }] = await Promise.all([
    db.from("role_permissions").select("role, key, allowed"),
    db.from("user_permissions").select("user_id, key, allowed"),
    db.from("users").select("*").neq("role", "parent").order("staff_id"),
    db.from("login_sessions").select("user_id").is("revoked_at", null),
  ]);

  const roleOverrides: Record<Role, Overrides> = { admin: {}, management: {}, reception: {}, faculty: {}, parent: {} };
  for (const r of (roleRows ?? []) as { role: Role; key: PermissionKey; allowed: boolean }[]) roleOverrides[r.role][r.key] = r.allowed;
  const userOverrides = new Map<string, Overrides>();
  for (const r of (userRows ?? []) as { user_id: string; key: PermissionKey; allowed: boolean }[]) {
    const o = userOverrides.get(r.user_id) ?? {};
    o[r.key] = r.allowed;
    userOverrides.set(r.user_id, o);
  }
  const activeSessions = new Map<string, number>();
  for (const s of (sessions ?? []) as { user_id: string }[]) activeSessions.set(s.user_id, (activeSessions.get(s.user_id) ?? 0) + 1);

  const rows: MatrixRow[] = PERMISSION_KEYS.map((key) => {
    const def = PERMISSIONS[key] as { label: string; hint?: string; parent: string };
    return {
      key,
      label: def.label,
      hint: def.hint,
      parent: def.parent,
      cells: STAFF_ROLES.map((role) => {
        const value = roleValue(role, key, roleOverrides[role]);
        return { role, value, locked: isLocked(role, key), isDefault: value === roleDefault(role, key) };
      }),
    };
  });

  const staff = ((people ?? []) as AppUser[]).filter((p) => !roleFilter || p.role === roleFilter);

  return (
    <>
      <PageHeader title="Access control" subtitle="Admin only · every change goes to the activity log" back="/more" />
      <Page wide>
        <Banner tone="navy" icon={ShieldCheck}>
          Switch access on or off for a whole role, or change it for one person below. Admin always has everything, and Admin-only controls
          (AI actions, promotion, access control, activity log, backup) cannot be given to anyone else. Parents always see only their own child.
        </Banner>

        <Section title="Access by role">
          <Matrix rows={rows} />
        </Section>

        <Section title="Add a staff member">
          <Card className="p-4">
            <AddStaff />
          </Card>
        </Section>

        <Section
          title={`People (${staff.length})`}
          action={
            <div className="flex gap-1.5 text-[12.5px] font-bold">
              {["", ...STAFF_ROLES].map((r) => (
                <a key={r} href={r ? `?role=${r}` : "?"} className={`rounded-full px-2.5 py-1 ${(roleFilter ?? "") === r ? "bg-primary text-white" : "bg-card text-muted"}`}>
                  {r ? ROLE_LABEL[r as Role] : "All"}
                </a>
              ))}
            </div>
          }
        >
          <Card className="divide-y divide-line overflow-hidden">
            {staff.map((p) => {
              const mine = userOverrides.get(p.id) ?? {};
              const summary = overrideSummary(p.role, roleOverrides[p.role], mine);
              const self = p.id === viewer.user.id;
              return (
                <details key={p.id} className="group">
                  <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 hover:bg-field">
                    <span className="w-14 font-mono text-[13px] font-bold text-navy">{p.staff_id}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold">
                        {p.name} {self && <span className="text-xs text-muted">(you)</span>}
                      </span>
                      <span className="block text-[12px] text-muted">
                        {ROLE_LABEL[p.role]} · {formatMobile(p.mobile)}
                        {summary ? <span className="text-violet"> · {summary}</span> : null}
                      </span>
                    </span>
                    {p.status === "active" ? <Chip tone="ok">Active</Chip> : <Chip tone="danger">Suspended</Chip>}
                    <span className="text-[11.5px] text-faint">{activeSessions.get(p.id) ?? 0} signed in</span>
                  </summary>
                  <div className="space-y-4 bg-field/60 px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      {!self && (
                        <form action={setSuspended}>
                          <input type="hidden" name="user_id" value={p.id} />
                          <input type="hidden" name="suspend" value={p.status === "active" ? "1" : "0"} />
                          {p.status === "active" ? (
                            <button className="btn btn-danger py-1.5 text-[13px]">
                              <UserX size={15} /> Suspend login
                            </button>
                          ) : (
                            <button className="btn btn-green py-1.5 text-[13px]">
                              <UserCheck size={15} /> Restore login
                            </button>
                          )}
                        </form>
                      )}
                      <form action={logoutEverywhere}>
                        <input type="hidden" name="user_id" value={p.id} />
                        <button className="btn btn-ghost py-1.5 text-[13px]">
                          <LogOut size={15} /> Log out everywhere
                        </button>
                      </form>
                    </div>
                    {p.role === "admin" ? (
                      <p className="text-[13px] text-muted">Admin has every permission. Nothing to change here.</p>
                    ) : (
                      <form action={savePersonAccess} className="space-y-2">
                        <input type="hidden" name="user_id" value={p.id} />
                        <p className="text-[13px] font-bold text-navy">Access for {p.name} only</p>
                        <div className="grid gap-x-6 gap-y-1.5 md:grid-cols-2">
                          {PERMISSION_KEYS.filter((k) => !isLocked(p.role, k)).map((k) => {
                            const base = roleValue(p.role, k, roleOverrides[p.role]);
                            const cur = mine[k];
                            return (
                              <label key={k} className="flex items-center justify-between gap-3 text-[13px]">
                                <span className={cur !== undefined ? "font-semibold text-violet" : ""}>{PERMISSIONS[k].label}</span>
                                <select name={k} defaultValue={cur === undefined ? "default" : cur ? "allow" : "deny"} className="field w-auto py-1 text-[13px]">
                                  <option value="default">Role ({base ? "yes" : "no"})</option>
                                  <option value="allow">Yes</option>
                                  <option value="deny">No</option>
                                </select>
                              </label>
                            );
                          })}
                        </div>
                        <button className="btn btn-primary py-1.5 text-[13px]">Save access for {p.name.split(" ")[0]}</button>
                      </form>
                    )}
                  </div>
                </details>
              );
            })}
          </Card>
        </Section>
      </Page>
    </>
  );
}
