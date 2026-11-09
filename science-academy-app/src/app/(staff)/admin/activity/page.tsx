import Link from "next/link";
import { Activity, ChevronLeft, ChevronRight } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { ACTION_LABEL } from "@/lib/activity";
import { dateTimeLabel } from "@/lib/format";
import type { AppUser } from "@/lib/types";
import { Card, Empty, Page, PageHeader } from "@/components/ui";
import { getT } from "@/lib/i18n/server";
import type { DictKey, TFn } from "@/lib/i18n";

/** The action in the reader's language (English label as fallback). */
function actionText(t: TFn, action: string): string {
  const key = `admin.action.${action}` as DictKey;
  const text = t(key);
  return text === key ? (ACTION_LABEL[action] ?? action) : text;
}

function groupText(t: TFn, group: string): string {
  const key = `admin.actionGroup.${group}` as DictKey;
  const text = t(key);
  return text === key ? group.charAt(0).toUpperCase() + group.slice(1) : text;
}

export async function generateMetadata() {
  const { t } = await getT();
  return { title: t("admin.activity.title") };
}

const PAGE_SIZE = 50;

type LogRow = {
  id: number;
  actor_id: string | null;
  actor_label: string;
  action: string;
  entity: string | null;
  entity_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

/** "amount: 2500 · modes: upi" — short, one line per entry. */
function compact(details: Record<string, unknown>): string {
  return Object.entries(details ?? {})
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => {
      const text = Array.isArray(v) ? v.map((x) => (typeof x === "object" ? JSON.stringify(x) : String(x))).join("; ") : typeof v === "object" ? JSON.stringify(v) : String(v);
      return `${k.replace(/_/g, " ")}: ${text}`;
    })
    .join(" · ")
    .slice(0, 400);
}

export default async function ActivityPage({ searchParams }: { searchParams: Promise<{ actor?: string; action?: string; page?: string }> }) {
  await requirePermission("admin.activity");
  const { t } = await getT();
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page) || 1);
  const db = adminClient();
  let q = db
    .from("activity_log")
    .select("*", { count: "exact" })
    .order("created_at", { ascending: false })
    .range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);
  if (sp.actor) q = q.eq("actor_id", sp.actor);
  if (sp.action) q = sp.action.endsWith(".") ? q.like("action", `${sp.action}%`) : q.eq("action", sp.action);
  const [{ data, count }, { data: staff }] = await Promise.all([q, db.from("users").select("id, staff_id, name").neq("role", "parent").order("staff_id")]);
  const rows = (data ?? []) as LogRow[];
  const pages = Math.max(1, Math.ceil((count ?? 0) / PAGE_SIZE));
  const link = (p: number) => {
    const u = new URLSearchParams();
    if (sp.actor) u.set("actor", sp.actor);
    if (sp.action) u.set("action", sp.action);
    u.set("page", String(p));
    return `?${u.toString()}`;
  };
  const groups = [...new Set(Object.keys(ACTION_LABEL).map((k) => k.split(".")[0]))];

  return (
    <>
      <PageHeader title={t("admin.activity.title")} subtitle={t("admin.activity.subtitle", { n: count ?? 0 })} back="/more" />
      <Page wide>
        <form className="mb-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <select name="actor" defaultValue={sp.actor ?? ""} className="field">
            <option value="">{t("admin.activity.everyone")}</option>
            {((staff ?? []) as Pick<AppUser, "id" | "staff_id" | "name">[]).map((u) => (
              <option key={u.id} value={u.id}>
                {u.staff_id} {u.name}
              </option>
            ))}
          </select>
          <select name="action" defaultValue={sp.action ?? ""} className="field">
            <option value="">{t("admin.activity.allActions")}</option>
            {groups.map((g) => (
              <optgroup key={g} label={groupText(t, g)}>
                <option value={`${g}.`}>{t("admin.activity.allOfGroup", { group: groupText(t, g) })}</option>
                {Object.entries(ACTION_LABEL)
                  .filter(([k]) => k.startsWith(`${g}.`))
                  .map(([k]) => (
                    <option key={k} value={k}>
                      {actionText(t, k)}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
          <button className="btn btn-primary">{t("admin.activity.filter")}</button>
        </form>

        {rows.length === 0 ? (
          <Empty icon={Activity}>{sp.actor || sp.action ? t("admin.activity.nothingFilter") : t("admin.activity.nothingYet")}</Empty>
        ) : (
          <Card className="divide-y divide-line overflow-hidden">
            {rows.map((r) => (
              <div key={r.id} className="grid grid-cols-1 gap-x-4 gap-y-0.5 px-4 py-2.5 text-[13.5px] md:grid-cols-[150px_180px_1fr]">
                <span className="text-[12px] text-muted md:text-[13px]">{dateTimeLabel(r.created_at)}</span>
                <span className="font-semibold text-navy">{r.actor_label}</span>
                <span className="min-w-0">
                  <span className="font-semibold">{actionText(t, r.action)}</span>
                  {r.details && Object.keys(r.details).length > 0 && <span className="block truncate text-[12px] text-muted md:whitespace-normal">{compact(r.details)}</span>}
                </span>
              </div>
            ))}
          </Card>
        )}

        {pages > 1 && (
          <div className="mt-3 flex items-center justify-between text-[13px] font-bold">
            {page > 1 ? (
              <Link href={link(page - 1)} className="btn btn-ghost py-1.5">
                <ChevronLeft size={15} /> {t("admin.activity.newer")}
              </Link>
            ) : (
              <span />
            )}
            <span className="text-muted">
              {t("admin.activity.page", { page, pages })}
            </span>
            {page < pages ? (
              <Link href={link(page + 1)} className="btn btn-ghost py-1.5">
                {t("admin.activity.older")} <ChevronRight size={15} />
              </Link>
            ) : (
              <span />
            )}
          </div>
        )}
      </Page>
    </>
  );
}
