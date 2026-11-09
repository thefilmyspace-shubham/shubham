"use client";

import { createContext, useContext, useMemo } from "react";
import { DEFAULT_LANG, translator, type Lang, type TFn } from "@/lib/i18n";

const LangContext = createContext<Lang>(DEFAULT_LANG);

export function I18nProvider({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  return <LangContext.Provider value={lang}>{children}</LangContext.Provider>;
}

export function useLang(): Lang {
  return useContext(LangContext);
}

export function useT(): TFn {
  const lang = useLang();
  return useMemo(() => translator(lang), [lang]);
}
