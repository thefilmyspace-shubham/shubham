import { DatabaseBackup, Download, Info } from "lucide-react";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { dateTimeLabel } from "@/lib/format";
import { Banner, Card, Empty, Page, PageHeader, Section } from "@/components/ui";
import { MakeBackup } from "./MakeBackup";

export const metadata = { title: "Backup" };

export default async function BackupPage() {
  await requirePermission("admin.backup");
  const { data } = await adminClient().from("backups").select("id, file_path, rows_total, created_at").order("created_at", { ascending: false }).limit(60);
  const list = (data ?? []) as { id: string; file_path: string; rows_total: number; created_at: string }[];
  return (
    <>
      <PageHeader title="Backup" subtitle="Daily Excel backup of all data" back="/more" />
      <Page>
        <Banner tone="navy" icon={Info}>
          A backup is made every night automatically: one Excel file with a sheet per table (students, guardians, fees, bills, attendance, marks,
          groups and more). Files are private; every download is written to the activity log. Keep a copy somewhere safe.
        </Banner>
        <div className="pt-4">
          <MakeBackup />
        </div>
        <Section title={`Backups (${list.length})`}>
          {list.length === 0 ? (
            <Empty icon={DatabaseBackup}>No backups yet. The first one is made tonight, or press the button above.</Empty>
          ) : (
            <Card className="divide-y divide-line overflow-hidden">
              {list.map((b) => (
                <div key={b.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{b.file_path.split("/").pop()?.replace(/^[0-9a-f-]{36}-/, "")}</p>
                    <p className="text-[12px] text-muted">
                      {dateTimeLabel(b.created_at)} · {b.rows_total.toLocaleString("en-IN")} rows
                    </p>
                  </div>
                  <a href={`/api/backup/${b.id}`} className="btn btn-soft py-1.5 text-[13px]">
                    <Download size={15} /> Download
                  </a>
                </div>
              ))}
            </Card>
          )}
        </Section>
      </Page>
    </>
  );
}
