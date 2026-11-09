// Per-person UI language: English, Hindi or Hinglish. Shared by server and client code.
import { DICT_EN, DICT_HI, DICT_HINGLISH, type DictKey } from "./dict";

export const LANGS = ["en", "hi", "hinglish"] as const;
export type Lang = (typeof LANGS)[number];
export type { DictKey };

export const LANG_LABEL: Record<Lang, string> = { en: "English", hi: "हिंदी", hinglish: "Hinglish" };

/** Used until a person picks a language. */
export const DEFAULT_LANG: Lang = "en";
/** Remembers the choice on this device, so the login screen matches it too. */
export const LANG_COOKIE = "sa_lang";

export const DICTS: Record<Lang, Record<DictKey, string>> = { en: DICT_EN, hi: DICT_HI, hinglish: DICT_HINGLISH };

export type Params = Record<string, string | number>;
export type TFn = (key: DictKey, params?: Params) => string;
/** The same text in every language; resolved for the reader when shown or sent. */
export type Localized = Record<Lang, string>;

export function isLang(value: unknown): value is Lang {
  return value === "en" || value === "hi" || value === "hinglish";
}

export function asLang(value: unknown): Lang {
  return isLang(value) ? value : DEFAULT_LANG;
}

/** "Hello {name}" with params; falls back to English, then to the key itself. */
export function t(lang: Lang, key: DictKey, params?: Params): string {
  const dicts = DICTS as Record<Lang, Record<string, string>>;
  const text: string = dicts[lang][key] || dicts.en[key] || key;
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (m, name: string) => (name in params ? String(params[name]) : m));
}

export function translator(lang: Lang): TFn {
  return (key, params) => t(lang, key, params);
}

/** Builds a Localized text by rendering `fn` once per language. */
export function localize(fn: (t: TFn, lang: Lang) => string): Localized {
  return Object.fromEntries(LANGS.map((l) => [l, fn(translator(l), l)])) as Localized;
}

/** A dictionary entry in every language (for notifications sent to many people). */
export function all(key: DictKey, params?: Params): Localized {
  return localize((tr) => tr(key, params));
}

export function pick(text: string | Localized, lang: Lang): string {
  return typeof text === "string" ? text : text[lang] || text.en;
}

/** <html lang>: Hindi pages are "hi", English and Hinglish are "en". */
export function htmlLang(lang: Lang): string {
  return lang === "hi" ? "hi" : "en";
}
