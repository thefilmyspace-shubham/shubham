"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";

/** Opens a notification: marks it read and goes to its page. */
export async function openNotification(formData: FormData) {
  const viewer = await getViewer();
  if (!viewer) redirect("/login");
  const id = String(formData.get("id") ?? "");
  const { data } = await adminClient()
    .from("notifications")
    .update({ read_at: new Date().toISOString() })
    .eq("id", id)
    .eq("user_id", viewer.user.id)
    .select("link")
    .maybeSingle<{ link: string | null }>();
  const home = viewer.user.role === "parent" ? "/parent" : "/";
  const link = data?.link && data.link.startsWith("/") ? data.link : `${home === "/" ? "" : home}/notifications`;
  redirect(link);
}

export async function markAllRead() {
  const viewer = await getViewer();
  if (!viewer) redirect("/login");
  await adminClient()
    .from("notifications")
    .update({ read_at: new Date().toISOString() })
    .eq("user_id", viewer.user.id)
    .is("read_at", null);
  revalidatePath("/", "layout");
}
