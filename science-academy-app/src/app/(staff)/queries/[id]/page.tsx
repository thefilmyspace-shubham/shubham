import Link from "next/link";
import { notFound } from "next/navigation";
import { can, canSeeStudent, requirePermission } from "@/lib/auth";
import { getT } from "@/lib/i18n/server";
import { adminClient } from "@/lib/supabase/admin";
import { threadById, threadMessages } from "@/lib/queries";
import { formatMobile } from "@/lib/ids";
import type { AppUser, Student } from "@/lib/types";
import { PageHeader } from "@/components/ui";
import { QueryChat } from "@/components/query/QueryChat";
import { StatusButton } from "./StatusButton";

export const metadata = { title: "Parent query" };

export default async function QueryThreadPage({ params }: { params: Promise<{ id: string }> }) {
  const viewer = await requirePermission("queries.reply");
  const { t } = await getT();
  const { id } = await params;
  const thread = await threadById(id);
  if (!thread) notFound();
  const db = adminClient();
  const [{ data: student }, { data: parent }] = await Promise.all([
    db.from("students").select("*").eq("id", thread.student_id).maybeSingle<Student>(),
    db.from("users").select("*").eq("id", thread.parent_user_id).maybeSingle<AppUser>(),
  ]);
  if (!student || !canSeeStudent(viewer, student)) notFound();
  const lines = await threadMessages(thread.id);
  const roleName = (r: AppUser["role"] | null) => (r ? t(`core.role.${r}`) : "");
  return (
    <>
      <PageHeader
        title={student.name}
        subtitle={`${t("groups.query.parentOf", { parent: parent?.name ?? "", student: student.code ?? "" })}${parent && can(viewer, "students.contacts") ? ` · ${formatMobile(parent.mobile)}` : ""}`}
        back="/queries"
        right={<StatusButton threadId={thread.id} status={thread.status} />}
      />
      <div className="mx-auto w-full max-w-4xl lg:px-8 lg:pt-2 lg:pb-6">
        <p className="px-4 pb-2 text-xs lg:px-0">
          <Link href={`/students/${student.id}`} className="font-bold text-primary">
            {student.code} →
          </Link>
        </p>
        <QueryChat
          mode="staff"
          threadId={thread.id}
          lines={lines.map((m) => ({
            id: m.id,
            mine: m.sender_id === viewer.user.id,
            from: m.senderRole === "parent" ? m.senderName : `${m.senderName} · ${roleName(m.senderRole)}`,
            body: m.body,
            attachment: m.attachment_name,
            createdAt: m.created_at,
          }))}
        />
      </div>
    </>
  );
}
