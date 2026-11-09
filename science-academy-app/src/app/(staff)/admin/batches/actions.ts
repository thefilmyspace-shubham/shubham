"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { can, staffForApi } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";

export type BatchState = { ok: boolean; message: string | null; at: number };

async function admin() {
  const viewer = await staffForApi();
  return viewer && can(viewer, "admin.access") ? viewer : null;
}

const BatchForm = z.object({
  id: z.string().uuid().optional(),
  board: z.enum(["CB", "MP"]),
  class: z.coerce.number().int().min(6).max(12),
  name: z.string().trim().min(1).max(40),
  start_time: z.string().trim().max(20),
});

/** "8 am" / "08:00" / "8:00 AM" → "8:00 AM". */
function tidyTime(text: string): string | null {
  const m = /^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i.exec(text.trim());
  if (!m) return text.trim() || null;
  let h = Number(m[1]);
  const min = m[2] ?? "00";
  let ampm = m[3]?.toUpperCase();
  if (!ampm) {
    ampm = h >= 12 ? "PM" : "AM";
    if (h > 12) h -= 12;
  }
  if (h === 0) h = 12;
  return `${h}:${min} ${ampm}`;
}

export async function saveBatch(_prev: BatchState, formData: FormData): Promise<BatchState> {
  const viewer = await admin();
  if (!viewer) return { ok: false, message: "Only Admin can change batches.", at: Date.now() };
  const parsed = BatchForm.safeParse({
    id: formData.get("id") || undefined,
    board: formData.get("board"),
    class: formData.get("class"),
    name: formData.get("name"),
    start_time: formData.get("start_time") ?? "",
  });
  if (!parsed.success) return { ok: false, message: "Fill board, class and a batch name.", at: Date.now() };
  const row = { board: parsed.data.board, class: parsed.data.class, name: parsed.data.name, start_time: tidyTime(parsed.data.start_time) };
  const db = adminClient();
  const q = parsed.data.id ? db.from("batches").update(row).eq("id", parsed.data.id) : db.from("batches").insert(row);
  const { data, error } = await q.select("id").single<{ id: string }>();
  if (error || !data) {
    const dup = error?.code === "23505";
    return { ok: false, message: dup ? "This batch already exists." : "Could not save the batch.", at: Date.now() };
  }
  // Keep the parents' group name in step with the batch.
  if (parsed.data.id) {
    const board = row.board === "CB" ? "CBSE" : "MP Board";
    await db.from("groups").update({ name: `${board} ${row.class} · ${row.name}${row.start_time ? ` ${row.start_time}` : ""}` }).eq("batch_id", data.id);
  }
  await logActivity(viewer, "batch.save", { type: "batch", id: data.id }, { ...row, new: !parsed.data.id });
  revalidatePath("/admin/batches");
  return { ok: true, message: parsed.data.id ? "Batch saved." : "Batch added. Its parents' group is ready.", at: Date.now() };
}

export async function setBatchActive(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const id = String(formData.get("id") ?? "");
  const active = formData.get("active") === "1";
  const db = adminClient();
  if (!active) {
    const { count } = await db.from("students").select("id", { count: "exact", head: true }).eq("batch_id", id).eq("status", "active");
    if ((count ?? 0) > 0) return; // The page hides the button while students are in it.
  }
  await db.from("batches").update({ active }).eq("id", id);
  await logActivity(viewer, "batch.save", { type: "batch", id }, { active });
  revalidatePath("/admin/batches");
}

export async function assignFaculty(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const batchId = String(formData.get("batch_id") ?? "");
  const userId = String(formData.get("user_id") ?? "");
  const subject = String(formData.get("subject") ?? "").trim() || null;
  const db = adminClient();
  const { data: person } = await db.from("users").select("staff_id, name, role").eq("id", userId).maybeSingle<{ staff_id: string; name: string; role: string }>();
  if (!person || person.role !== "faculty") return;
  await db.from("faculty_batches").upsert({ user_id: userId, batch_id: batchId, subject });
  await logActivity(viewer, "batch.save", { type: "batch", id: batchId }, { faculty_added: `${person.staff_id} ${person.name}`, subject });
  revalidatePath("/admin/batches");
}

export async function removeFaculty(formData: FormData) {
  const viewer = await admin();
  if (!viewer) return;
  const batchId = String(formData.get("batch_id") ?? "");
  const userId = String(formData.get("user_id") ?? "");
  await adminClient().from("faculty_batches").delete().eq("batch_id", batchId).eq("user_id", userId);
  await logActivity(viewer, "batch.save", { type: "batch", id: batchId }, { faculty_removed: userId });
  revalidatePath("/admin/batches");
}
