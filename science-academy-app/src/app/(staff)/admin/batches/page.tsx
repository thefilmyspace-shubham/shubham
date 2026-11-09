import { Layers, Pencil, X } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { allBatches, batchShort } from "@/lib/batches";
import { boardName } from "@/lib/ids";
import type { AppUser, Batch } from "@/lib/types";
import { Card, Chip, Empty, Page, PageHeader, Section } from "@/components/ui";
import { BatchForm } from "./BatchForm";
import { assignFaculty, removeFaculty, setBatchActive } from "./actions";
import { getT } from "@/lib/i18n/server";

export async function generateMetadata() {
  const { t } = await getT();
  return { title: t("admin.batches.title") };
}

export default async function BatchesPage() {
  await requirePermission("admin.access");
  const { t } = await getT();
  const db = adminClient();
  const [batches, { data: fb }, { data: faculty }, { data: students }] = await Promise.all([
    allBatches(true),
    db.from("faculty_batches").select("user_id, batch_id, subject"),
    db.from("users").select("*").eq("role", "faculty").eq("status", "active").order("staff_id"),
    db.from("students").select("batch_id").eq("status", "active"),
  ]);
  const links = (fb ?? []) as { user_id: string; batch_id: string; subject: string | null }[];
  const facultyList = (faculty ?? []) as AppUser[];
  const people = new Map(facultyList.map((f) => [f.id, f]));
  const counts = new Map<string, number>();
  for (const s of (students ?? []) as { batch_id: string | null }[]) if (s.batch_id) counts.set(s.batch_id, (counts.get(s.batch_id) ?? 0) + 1);

  const groups = new Map<string, Batch[]>();
  for (const b of batches) {
    const k = t("admin.batches.classGroup", { board: boardName(b.board), cls: b.class });
    groups.set(k, [...(groups.get(k) ?? []), b]);
  }

  return (
    <>
      <PageHeader title={t("admin.batches.title")} subtitle={t("admin.batches.subtitle")} back="/more" />
      <Page>
        <Section title={t("admin.batches.add")}>
          <Card className="p-4">
            <BatchForm />
          </Card>
        </Section>

        {batches.length === 0 && (
          <div className="pt-5">
            <Empty icon={Layers}>{t("admin.batches.none")}</Empty>
          </div>
        )}

        {[...groups.entries()].map(([title, list]) => (
          <Section key={title} title={title}>
            <div className="space-y-2.5">
              {list.map((b) => {
                const teachers = links.filter((l) => l.batch_id === b.id);
                const n = counts.get(b.id) ?? 0;
                return (
                  <Card key={b.id} className={`p-4 ${b.active ? "" : "opacity-60"}`}>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="flex-1 font-bold text-navy">{batchShort(b)}</p>
                      <Chip tone="navy">{t("admin.batches.nStudents", { n })}</Chip>
                      {!b.active && <Chip tone="danger">{t("admin.batches.inactive")}</Chip>}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {teachers.length === 0 && <span className="text-[12.5px] text-muted">{t("admin.batches.noFaculty")}</span>}
                      {teachers.map((link) => {
                        const p = people.get(link.user_id);
                        return (
                          <form key={link.user_id} action={removeFaculty} className="inline-flex">
                            <input type="hidden" name="batch_id" value={b.id} />
                            <input type="hidden" name="user_id" value={link.user_id} />
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary-soft py-0.5 pr-1 pl-2.5 text-[12px] font-bold text-primary">
                              {p ? `${p.staff_id} ${p.name}` : t("admin.batches.formerFaculty")}
                              {link.subject ? ` · ${link.subject}` : ""}
                              <button className="grid h-5 w-5 place-items-center rounded-full hover:bg-white" aria-label={t("admin.batches.remove")}>
                                <X size={12} />
                              </button>
                            </span>
                          </form>
                        );
                      })}
                    </div>
                    <details className="mt-3">
                      <summary className="inline-flex cursor-pointer items-center gap-1 text-[13px] font-bold text-primary">
                        <Pencil size={13} /> {t("admin.batches.edit")}
                      </summary>
                      <div className="mt-3 space-y-4">
                        <BatchForm batch={{ id: b.id, board: b.board, class: b.class, name: b.name, start_time: b.start_time }} />
                        {facultyList.length > 0 && (
                          <form action={assignFaculty} className="grid grid-cols-2 gap-3 md:grid-cols-5">
                            <input type="hidden" name="batch_id" value={b.id} />
                            <div className="col-span-2">
                              <label className="label">{t("admin.batches.faculty")}</label>
                              <select name="user_id" className="field" required>
                                {facultyList.map((f) => (
                                  <option key={f.id} value={f.id}>
                                    {f.staff_id} {f.name}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="col-span-2">
                              <label className="label">{t("admin.batches.subject")}</label>
                              <input name="subject" className="field" placeholder="Physics" />
                            </div>
                            <div className="col-span-2 flex items-end md:col-span-1">
                              <button className="btn btn-soft w-full">{t("admin.batches.assign")}</button>
                            </div>
                          </form>
                        )}
                        <form action={setBatchActive}>
                          <input type="hidden" name="id" value={b.id} />
                          <input type="hidden" name="active" value={b.active ? "0" : "1"} />
                          {b.active ? (
                            n > 0 ? (
                              <p className="text-[12.5px] text-muted">{t("admin.batches.moveFirst", { n })}</p>
                            ) : (
                              <button className="btn btn-danger py-1.5 text-[13px]">{t("admin.batches.makeInactive")}</button>
                            )
                          ) : (
                            <button className="btn btn-green py-1.5 text-[13px]">{t("admin.batches.makeActive")}</button>
                          )}
                        </form>
                      </div>
                    </details>
                  </Card>
                );
              })}
            </div>
          </Section>
        ))}
      </Page>
    </>
  );
}
