import Link from "next/link";
import { ShieldOff } from "lucide-react";
import { getT } from "@/lib/i18n/server";

export default async function NotFound() {
  const { t } = await getT();
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 px-6 pt-24 text-center">
      <ShieldOff size={36} className="text-faint" />
      <h1 className="text-lg font-extrabold text-navy">{t("core.notFound.title")}</h1>
      <p className="text-sm text-muted">{t("core.notFound.text")}</p>
      <Link href="/" className="btn btn-primary mt-2">
        {t("core.notFound.home")}
      </Link>
    </div>
  );
}
