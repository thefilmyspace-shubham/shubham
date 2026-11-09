"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import { can, canSeeBatch, requireStaff, type StaffViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { ensureParentUser, notify } from "@/lib/notify";
import type { Batch, Test } from "@/lib/types";
import { all } from "@/lib/i18n";

async function editor(): Promise<StaffViewer> {
  const viewer = await requireStaff();
  if (!can(viewer, "academics.edit")) redirect("/timetable?error=access");
  return viewer;
}

const uuid = z.string().uuid();
const time = z.string().regex(/^\d{2}:\d{2}(:\d{2})?$/);

const EntryForm = z.object({
  id: uuid.optional().or(z.literal("")),
  batch_id: uuid,
  weekday: z.coerce.number().int().min(1).max(7),
  start_time: time,
  end_time: time.optional().or(z.literal("")),
  subject: z.string().trim().min(1).max(80),
  faculty_id: uuid.optional().or(z.literal("")),
  tag: z.enum(["School", "Coaching"]),
});

/** Adds or changes one weekly timetable class. */
export async function saveEntry(form: FormData) {
  const viewer = await editor();
  const parsed = EntryForm.safeParse(Object.fromEntries(form));
  if (!parsed.success) redirect("/timetable?error=entry");
  const e = parsed.data;
  if (e.end_time && e.end_time <= e.start_time) redirect(`/timetable?batch=${e.batch_id}&error=time`);
  const db = adminClient();
  if (e.faculty_id) {
    const { data: f } = await db.from("users").select("id").eq("id", e.faculty_id).eq("role", "faculty").maybeSingle();
    if (!f) redirect(`/timetable?batch=${e.batch_id}&error=entry`);
  }
  const row = {
    batch_id: e.batch_id,
    weekday: e.weekday,
    start_time: e.start_time,
    end_time: e.end_time || null,
    subject: e.subject,
    faculty_id: e.faculty_id || null,
    tag: e.tag,
  };
  const { data, error } = e.id
    ? await db.from("timetable_entries").update(row).eq("id", e.id).select("id").single()
    : await db.from("timetable_entries").insert(row).select("id").single();
  if (error || !data) redirect(`/timetable?batch=${e.batch_id}&error=entry`);
  await logActivity(viewer, "timetable.save", { type: "timetable_entry", id: data.id }, { ...row, edited: Boolean(e.id) });
  revalidatePath("/timetable");
  redirect(`/timetable?batch=${e.batch_id}&saved=timetable`);
}

export async function deleteEntry(form: FormData) {
  const viewer = await editor();
  const id = String(form.get("id") ?? "");
  if (!uuid.safeParse(id).success) redirect("/timetable");
  const { data } = await adminClient().from("timetable_entries").delete().eq("id", id).select("*").maybeSingle();
  if (data) await logActivity(viewer, "timetable.save", { type: "timetable_entry", id }, { deleted: data });
  revalidatePath("/timetable");
  redirect(`/timetable?batch=${data?.batch_id ?? ""}&saved=timetable`);
}

const TestForm = z.object({
  id: uuid.optional().or(z.literal("")),
  name: z.string().trim().min(2).max(120),
  for: z.string(),
  subject: z.string().trim().max(80).optional(),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  start_time: time.optional().or(z.literal("")),
  tag: z.enum(["School", "Coaching"]),
  max_marks: z.coerce.number().positive().max(1000).optional().or(z.literal("")),
});

/** "for" is either "class:CB:9" (whole class) or "batch:<id>". */
async function resolveFor(value: string): Promise<{ board: "CB" | "MP"; class: number; batch_id: string | null } | null> {
  const cls = /^class:(CB|MP):(6|7|8|9|10|11|12)$/.exec(value);
  if (cls) return { board: cls[1] as "CB" | "MP", class: Number(cls[2]), batch_id: null };
  const b = /^batch:([0-9a-f-]{36})$/i.exec(value);
  if (!b) return null;
  const { data } = await adminClient().from("batches").select("*").eq("id", b[1]).maybeSingle<Batch>();
  return data ? { board: data.board, class: data.class, batch_id: data.id } : null;
}

/** Adds or changes a test or exam (School or Coaching). */
export async function saveTest(form: FormData) {
  const viewer = await editor();
  const parsed = TestForm.safeParse(Object.fromEntries(form));
  const back = `/timetable/test${form.get("id") ? `?id=${form.get("id")}` : ""}`;
  if (!parsed.success) redirect(`${back}${back.includes("?") ? "&" : "?"}error=form`);
  const t = parsed.data;
  const target = await resolveFor(t.for);
  if (!target) redirect(`${back}${back.includes("?") ? "&" : "?"}error=form`);
  const row = {
    name: t.name,
    board: target.board,
    class: target.class,
    batch_id: target.batch_id,
    subject: t.subject || null,
    date: t.date,
    start_time: t.start_time || null,
    tag: t.tag,
    max_marks: t.max_marks === "" || t.max_marks === undefined ? null : t.max_marks,
  };
  const db = adminClient();
  const { data, error } = t.id
    ? await db.from("tests").update(row).eq("id", t.id).select("id").single()
    : await db.from("tests").insert({ ...row, created_by: viewer.user.id }).select("id").single();
  if (error || !data) redirect(`${back}${back.includes("?") ? "&" : "?"}error=save`);
  await logActivity(viewer, "test.save", { type: "test", id: data.id }, { ...row, edited: Boolean(t.id) });
  revalidatePath("/timetable");
  revalidatePath("/ranks");
  redirect(`/timetable?board=${target.board}&class=${target.class}&saved=test&test=${data.id}`);
}

/** Deletes a test that has no marks yet (tests with marks feed ranks and profiles). */
export async function deleteTest(form: FormData) {
  const viewer = await editor();
  const id = String(form.get("id") ?? "");
  if (!uuid.safeParse(id).success) redirect("/timetable");
  const db = adminClient();
  const { count } = await db.from("marks").select("test_id", { count: "exact", head: true }).eq("test_id", id);
  if ((count ?? 0) > 0) redirect(`/timetable/test?id=${id}&error=hasmarks`);
  const { data } = await db.from("tests").delete().eq("id", id).select("*").maybeSingle<Test>();
  if (data) await logActivity(viewer, "test.delete", { type: "test", id }, { name: data.name, date: data.date, board: data.board, class: data.class });
  revalidatePath("/timetable");
  redirect("/timetable?saved=deleted");
}

// ---------------------------------------------------------------------------
// Posting to batch groups: a separate step after saving.
// ---------------------------------------------------------------------------

/** Words that look like fee talk. Batch groups never carry fee messages (spec §9, §14). */
const FEE_WORDS = /(₹|\brs\.?\s*\d|\bfees?\b|\bdues?\b|\bbalance\b|\bpending amount\b)/i;

export async function postToGroups(form: FormData) {
  const viewer = await requireStaff();
  if (!can(viewer, "groups.post_batch")) redirect("/timetable?error=post");
  const kind = String(form.get("kind")) === "test" ? "test" : "timetable";
  const body = String(form.get("body") ?? "").trim().slice(0, 2000);
  const batchIds = form.getAll("batch").map(String).filter((id) => uuid.safeParse(id).success && canSeeBatch(viewer, id));
  const back = String(form.get("back") ?? "/timetable");
  const safeBack = back.startsWith("/timetable") ? back : "/timetable";
  if (!body || !batchIds.length) redirect(`${safeBack}${safeBack.includes("?") ? "&" : "?"}error=empty`);
  if (FEE_WORDS.test(body)) redirect(`${safeBack}${safeBack.includes("?") ? "&" : "?"}error=fees`);

  const db = adminClient();
  const { data: groups } = await db.from("groups").select("id, batch_id, name").eq("kind", "batch").in("batch_id", batchIds);
  let posted = 0;
  for (const g of (groups ?? []) as { id: string; batch_id: string; name: string }[]) {
    const { data: msg } = await db
      .from("messages")
      .insert({ group_id: g.id, sender_id: viewer.user.id, type: kind, body })
      .select("id")
      .single<{ id: string }>();
    if (!msg) continue;
    posted++;
    await logActivity(viewer, "group.post", { type: "group", id: g.id }, { message: msg.id, type: kind });

    // Every parent login of an active student in the batch gets a notification.
    const { data: links } = await db
      .from("guardians")
      .select("mobile, name, students!inner(batch_id, status)")
      .eq("is_login_number", true)
      .eq("students.batch_id", g.batch_id)
      .eq("students.status", "active");
    const seen = new Set<string>();
    const items = [];
    for (const l of (links ?? []) as { mobile: string; name: string | null }[]) {
      if (seen.has(l.mobile)) continue;
      seen.add(l.mobile);
      const parent = await ensureParentUser(l.mobile, l.name ?? "Parent");
      if (!parent) continue;
      items.push({
        userId: parent.id,
        kind: "group_post",
        title: all(kind === "test" ? "academics.post.notifTest" : "academics.post.notifTimetable"),
        body: body.split("\n")[0].slice(0, 140),
        link: "/parent",
        dedupeKey: `post-${msg.id}`,
      });
    }
    await notify(items);
  }
  revalidatePath("/timetable");
  revalidatePath("/groups", "layout");
  revalidatePath("/parent");
  redirect(`/timetable?posted=${posted}`);
}
