import { requireParent } from "@/lib/auth";
import { getT } from "@/lib/i18n/server";
import { LanguagePicker } from "@/components/LanguagePicker";
import { Card } from "@/components/ui";

export const metadata = { title: "Language" };

/** Parent app: choose English, Hindi or Hinglish. */
export default async function ParentLanguagePage() {
  await requireParent();
  const { t } = await getT();
  return (
    <div className="mx-auto max-w-lg px-4 pt-4">
      <h1 className="mb-3 text-xl font-extrabold text-navy">{t("core.language")}</h1>
      <Card className="p-4">
        <LanguagePicker />
        <p className="mt-3 text-sm text-muted">{t("core.parent.languageHint")}</p>
      </Card>
    </div>
  );
}
