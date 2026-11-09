"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { getViewer } from "@/lib/auth";
import { adminClient } from "@/lib/supabase/admin";
import { LANG_COOKIE, isLang } from "@/lib/i18n";

/** Saves the language on this device and, when logged in, on the person's login. */
export async function setLanguage(lang: string): Promise<void> {
  if (!isLang(lang)) return;
  const jar = await cookies();
  jar.set(LANG_COOKIE, lang, { path: "/", maxAge: 60 * 60 * 24 * 400, sameSite: "lax" });
  const viewer = await getViewer().catch(() => null);
  if (viewer) {
    // Ignored if the language migration has not been run yet: the cookie still works.
    await adminClient().from("users").update({ language: lang }).eq("id", viewer.user.id);
  }
  revalidatePath("/", "layout");
}
