import "server-only";
import { cookies } from "next/headers";
import { getViewer } from "../auth";
import { LANG_COOKIE, asLang, isLang, translator, type Lang, type TFn } from "./index";

/** The signed-in person's language, else this device's last choice, else English. */
export async function getLang(): Promise<Lang> {
  // A database hiccup must not take down the login screen, so fall back quietly.
  const language = await getViewer()
    .then((viewer) => (viewer?.user as { language?: string | null } | undefined)?.language)
    .catch(() => null);
  if (isLang(language)) return language;
  return asLang((await cookies()).get(LANG_COOKIE)?.value);
}

export async function getT(): Promise<{ lang: Lang; t: TFn }> {
  const lang = await getLang();
  return { lang, t: translator(lang) };
}
