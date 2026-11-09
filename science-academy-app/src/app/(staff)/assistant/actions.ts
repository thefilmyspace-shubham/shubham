"use server";

import { revalidatePath } from "next/cache";
import { can, staffForApi } from "@/lib/auth";
import { askAssistant } from "@/lib/assistant/chat";
import { cancelAction, confirmAction } from "@/lib/assistant/actions";
import { adminClient } from "@/lib/supabase/admin";

export type AskState = { error: string | null; at: number };

export async function ask(_prev: AskState, formData: FormData): Promise<AskState> {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "ai.ask")) return { error: "This login cannot use the AI assistant.", at: Date.now() };
  const result = await askAssistant(viewer, String(formData.get("text") ?? ""));
  revalidatePath("/assistant");
  return { error: result.ok ? null : result.error, at: Date.now() };
}

export async function confirmAiAction(formData: FormData) {
  const viewer = await staffForApi();
  if (!viewer) return;
  await confirmAction(viewer, String(formData.get("id") ?? ""));
  revalidatePath("/assistant");
}

export async function cancelAiAction(formData: FormData) {
  const viewer = await staffForApi();
  if (!viewer) return;
  await cancelAction(viewer, String(formData.get("id") ?? ""));
  revalidatePath("/assistant");
}

export async function clearConversation() {
  const viewer = await staffForApi();
  if (!viewer || !can(viewer, "ai.ask")) return;
  await adminClient().from("ai_messages").delete().eq("user_id", viewer.user.id);
  revalidatePath("/assistant");
}
