"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requirePermission } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { logActivity } from "@/lib/activity";
import { formatStudentId } from "@/lib/ids";
import { recordIdChange } from "@/lib/students";
import type { Batch, Student } from "@/lib/types";

/**
 * Year-end promotion (Admin only): the whole class (or one batch) moves up.
 * Class and session year in the ID change, the roll stays; the old ID goes
 * into the history (still searchable). Class 12 students pass out.
 * Only students still in the chosen session are moved, so running it twice
 * never promotes anyone twice.
 */
export async function promoteClass(form: FormData) {
  const viewer = await requirePermission("admin.promotion");
  const board = String(form.get("board") ?? "");
  const cls = Number(form.get("class"));
  const fromSession = Number(form.get("from_session"));
  const batch = String(form.get("batch") ?? "") || null;
  const target = String(form.get("target_batch") ?? "") || null;
  if (!["CB", "MP"].includes(board) || !(cls >= 6 && cls <= 12) || !Number.isFinite(fromSession)) redirect("/admin/promotion");
  if (form.get("confirm") !== "on") redirect(`/admin/promotion?board=${board}&class=${cls}&error=confirm`);

  const db = adminClient();
  if (target && cls < 12) {
    const { data: tb } = await db.from("batches").select("*").eq("id", target).maybeSingle<Batch>();
    if (!tb || tb.board !== board || tb.class !== cls + 1) redirect(`/admin/promotion?board=${board}&class=${cls}&error=batch`);
  }

  let q = db.from("students").select("*").eq("status", "active").eq("board", board).eq("current_class", cls).eq("session_year", fromSession);
  if (batch) q = q.eq("batch_id", batch);
  const { data } = await q;
  const students = (data ?? []) as Student[];
  const now = new Date().toISOString();
  const changes: { from: string | null; to: string }[] = [];
  let passedOut = 0;

  for (const s of students) {
    if (cls === 12) {
      await db.from("students").update({ status: "passed_out", updated_at: now }).eq("id", s.id);
      passedOut++;
      continue;
    }
    const next = {
      current_class: cls + 1,
      session_year: (fromSession + 1) % 100,
      batch_id: target,
      updated_at: now,
    };
    const { data: row } = await db.from("students").update(next).eq("id", s.id).select("*").single<Student>();
    if (row) {
      await recordIdChange(row);
      changes.push({ from: s.code, to: formatStudentId(row.board, row.current_class, row.roll_number!, row.session_year) });
    }
  }

  await logActivity(viewer, "promotion.run", { type: "class", id: `${board}${cls}` }, {
    board,
    class: cls,
    from_session: fromSession,
    batch,
    target_batch: target,
    promoted: changes.length,
    passed_out: passedOut,
    sample: changes.slice(0, 5),
  });
  revalidatePath("/students");
  redirect(`/admin/promotion?done=${changes.length}&passed=${passedOut}&board=${board}&class=${cls}`);
}
