"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Languages, LoaderCircle } from "lucide-react";
import { LANGS, LANG_LABEL } from "@/lib/i18n";
import { setLanguage } from "@/app/actions/language";
import { useLang } from "./I18nProvider";

/** English · हिंदी · Hinglish. Saved on this device and on the login. */
export function LanguagePicker({ compact = false }: { compact?: boolean }) {
  const lang = useLang();
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <div className={`flex items-center gap-1.5 ${compact ? "" : "flex-wrap"}`} role="radiogroup" aria-label="Language / भाषा">
      {pending ? <LoaderCircle size={15} className="animate-spin text-muted" /> : <Languages size={15} className="text-muted" />}
      {LANGS.map((l) => (
        <button
          key={l}
          type="button"
          role="radio"
          aria-checked={lang === l}
          disabled={pending}
          onClick={() =>
            start(async () => {
              await setLanguage(l);
              router.refresh();
            })
          }
          className={`rounded-full border px-2.5 py-1 text-[12.5px] font-bold ${
            lang === l ? "border-primary bg-primary text-white" : "border-line bg-card text-fg hover:border-primary"
          }`}
        >
          {LANG_LABEL[l]}
        </button>
      ))}
    </div>
  );
}
