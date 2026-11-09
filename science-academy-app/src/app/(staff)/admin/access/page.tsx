import { SubmitButton } from "@/components/SubmitButton";
import { LogOut, ShieldCheck, UserCheck, UserX } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { formatMobile } from "@/lib/ids";
import {
  isLocked,
  PERMISSION_KEYS,
  PERMISSIONS,
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
import { logoutEverywhere, savePersonAccess, setSuspended, updateStaffContact } from "./actions";
import { otpChannel } from "@/lib/env";
import { getT } from "@/lib/i18n/server";
import type { DictKey, TFn } from "@/lib/i18n";

const HINT_KEY: Record<string, DictKey> = {
  "Faculty: own batches only": "admin.hint.ownBatchesOnly",
  "Faculty: own batches": "admin.hint.ownBatches",
  "Every correction is logged": "admin.hint.correctionLogged",
  "Off: only own batches": "admin.hint.offOwnBatches",
};
const PARENT_KEY: Record<string, DictKey> = {
  "Own child": "admin.parentAccess.ownChild",
  No: "admin.parentAccess.no",
  "Own child (status, receipts)": "admin.parentAccess.ownChildFees",
  "No (read only)": "admin.parentAccess.noReadOnly",
};

const permLabel = (t: TFn, key: PermissionKey) => t(`admin.perm.${key}`);

/** "1 extra: see ranks of all batches" in the reader's language. */
function summaryOf(t: TFn, role: Role, roleO: Overrides, mine: Overrides): string | null {
  const extra: string[] = [];
  const removed: string[] = [];
  for (const key of PERMISSION_KEYS) {
    const v = mine[key];
    if (v === undefined || isLocked(role, key)) continue;
    const base = roleValue(role, key, roleO);
    if (v && !base) extra.push(permLabel(t, key));
    if (!v && base) removed.push(permLabel(t, key));
  }
  const parts: string[] = [];
  if (extra.length) parts.push(t("admin.access.extra", { n: extra.length, list: extra.join(", ") }));
  if (removed.length) parts.push(t("admin.access.removed", { n: removed.length, list: removed.join(", ") }));
  return parts.length ? parts.join(" · ") : null;
}

export async function generateMetadata() {
  const { t } = await getT();
  return { title: t("admin.access.title") };
}

export default async function AccessPage({ searchParams }: { searchParams: Promise<{ role?: string }> }) {
  const viewer = await requirePermission("admin.access");
  const { t } = await getT();
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
      label: permLabel(t, key),
      hint: def.hint ? (HINT_KEY[def.hint] ? t(HINT_KEY[def.hint]) : def.hint) : undefined,
      parent: PARENT_KEY[def.parent] ? t(PARENT_KEY[def.parent]) : def.parent,
      cells: STAFF_ROLES.map((role) => {
        const value = roleValue(role, key, roleOverrides[role]);
        return { role, value, locked: isLocked(role, key), isDefault: value === roleDefault(role, key) };
      }),
    };
  });

  const staff = ((people ?? []) as AppUser[]).filter((p) => !roleFilter || p.role === roleFilter);

  return (
    <>
      <PageHeader title={t("admin.access.title")} subtitle={t("admin.access.subtitle")} back="/more" />
      <Page wide>
        <Banner tone="navy" icon={ShieldCheck}>
          {t("admin.access.banner")}
        </Banner>

        <Section title={t("admin.access.byRole")}>
          <Matrix rows={rows} />
        </Section>

        <Section title={t("admin.access.addStaff")}>
          <Card className="p-4">
            <AddStaff emailRequired={otpChannel() === "email"} />
          </Card>
        </Section>

        <Section
          title={t("admin.access.people", { n: staff.length })}
          action={
            <div className="flex flex-wrap gap-1.5 text-[12.5px] font-bold">
              {["", ...STAFF_ROLES].map((r) => (
                <a key={r} href={r ? `?role=${r}` : "?"} className={`rounded-full px-2.5 py-1 ${(roleFilter ?? "") === r ? "bg-primary text-white" : "bg-card text-muted"}`}>
                  {r ? t(`core.role.${r as Role}`) : t("core.all")}
                </a>
              ))}
            </div>
          }
        >
          <Card className="divide-y divide-line overflow-hidden">
            {staff.map((p) => {
              const mine = userOverrides.get(p.id) ?? {};
              const summary = summaryOf(t, p.role, roleOverrides[p.role], mine);
              const self = p.id === viewer.user.id;
              return (
                <details key={p.id} className="group">
                  <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 hover:bg-field">
                    <span className="w-14 font-mono text-[13px] font-bold text-navy">{p.staff_id}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold">
                        {p.name} {self && <span className="text-xs text-muted">{t("admin.access.you")}</span>}
                      </span>
                      <span className="block text-[12px] text-muted">
                        {t(`core.role.${p.role}`)} · {formatMobile(p.mobile)} · {p.email ?? <span className="font-semibold text-danger">{t("admin.access.noEmail")}</span>}
                        {summary ? <span className="text-violet"> · {summary}</span> : null}
                      </span>
                    </span>
                    {p.status === "active" ? <Chip tone="ok">{t("admin.access.active")}</Chip> : <Chip tone="danger">{t("admin.access.suspended")}</Chip>}
                    <span className="text-[11.5px] text-faint">{t("admin.access.signedIn", { n: activeSessions.get(p.id) ?? 0 })}</span>
                  </summary>
                  <div className="space-y-4 bg-field/60 px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      {!self && (
                        <form action={setSuspended}>
                          <input type="hidden" name="user_id" value={p.id} />
                          <input type="hidden" name="suspend" value={p.status === "active" ? "1" : "0"} />
                          {p.status === "active" ? (
                            <SubmitButton className="btn btn-danger py-1.5 text-[13px]">
                              <UserX size={15} /> {t("admin.access.suspend")}
                            </SubmitButton>
                          ) : (
                            <SubmitButton className="btn btn-green py-1.5 text-[13px]">
                              <UserCheck size={15} /> {t("admin.access.restore")}
                            </SubmitButton>
                          )}
                        </form>
                      )}
                      <form action={logoutEverywhere}>
                        <input type="hidden" name="user_id" value={p.id} />
                        <SubmitButton className="btn btn-ghost py-1.5 text-[13px]">
                          <LogOut size={15} /> {t("admin.access.logoutAll")}
                        </SubmitButton>
                      </form>
                    </div>
                    <form action={updateStaffContact} className="grid grid-cols-1 items-end gap-2 sm:grid-cols-[1fr_150px_1fr_auto]">
                      <input type="hidden" name="user_id" value={p.id} />
                      <div>
                        <label className="label">{t("admin.access.name")}</label>
                        <input name="name" defaultValue={p.name} className="field py-1.5 text-[14px]" required minLength={2} />
                      </div>
                      <div>
                        <label className="label">{t("admin.access.mobile")}</label>
                        <input name="mobile" defaultValue={p.mobile} className="field py-1.5 text-[14px]" inputMode="numeric" required />
                      </div>
                      <div>
                        <label className="label">{t("admin.access.emailCode")}</label>
                        <input name="email" type="email" defaultValue={p.email ?? ""} className="field py-1.5 text-[14px]" />
                      </div>
                      <SubmitButton className="btn btn-ghost py-1.5 text-[13px]">{t("admin.access.saveDetails")}</SubmitButton>
                    </form>
                    {p.role === "admin" ? (
                      <p className="text-[13px] text-muted">{t("admin.access.adminAll")}</p>
                    ) : (
                      <form action={savePersonAccess} className="space-y-2">
                        <input type="hidden" name="user_id" value={p.id} />
                        <p className="text-[13px] font-bold text-navy">{t("admin.access.forOnly", { name: p.name })}</p>
                        <div className="grid grid-cols-1 gap-x-6 gap-y-1.5 md:grid-cols-2">
                          {PERMISSION_KEYS.filter((k) => !isLocked(p.role, k)).map((k) => {
                            const base = roleValue(p.role, k, roleOverrides[p.role]);
                            const cur = mine[k];
                            return (
                              <label key={k} className="flex items-center justify-between gap-3 text-[13px]">
                                <span className={cur !== undefined ? "font-semibold text-violet" : ""}>{permLabel(t, k)}</span>
                                <select name={k} defaultValue={cur === undefined ? "default" : cur ? "allow" : "deny"} className="field w-auto py-1 text-[13px]">
                                  <option value="default">{t("admin.access.roleDefault", { value: base ? t("core.yes") : t("core.no") })}</option>
                                  <option value="allow">{t("core.yes")}</option>
                                  <option value="deny">{t("core.no")}</option>
                                </select>
                              </label>
                            );
                          })}
                        </div>
                        <SubmitButton className="btn btn-primary py-1.5 text-[13px]">{t("admin.access.saveFor", { name: p.name.split(" ")[0] })}</SubmitButton>
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
