import { redirect } from "next/navigation";
import { getViewer, homeFor } from "@/lib/auth";
import { Logo } from "@/components/Logo";
import { Footer } from "@/components/ui";
import { otpChannel } from "@/lib/env";
import { getT } from "@/lib/i18n/server";
import { LoginForm } from "./LoginForm";

export const metadata = { title: "Log in" };

export default async function LoginPage() {
  const viewer = await getViewer().catch(() => null);
  if (viewer) redirect(homeFor(viewer));
  const { t } = await getT();
  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden border-r border-line bg-card p-10 lg:flex">
        <div className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-navy via-primary to-green" />
        <Logo size={72} />
        <div className="max-w-lg">
          <p className="text-sm font-bold tracking-widest text-green uppercase">We believe in quality</p>
          <h1 className="mt-3 text-4xl leading-tight font-extrabold tracking-tight text-navy">
            {t("core.login.heroLine1")}
            <br />
            {t("core.login.heroLine2")}
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-muted">
            {t("core.login.heroText")}
          </p>
          <ul className="mt-6 flex flex-wrap gap-2 text-[13px] font-semibold">
            {[t("core.login.chipClasses"), t("core.login.chipBoards"), t("core.login.chipTests"), t("core.login.chipParents")].map((chip) => (
              <li key={chip} className="rounded-full bg-primary-soft px-3 py-1.5 text-primary">
                {chip}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-faint">Powered by TFS · The First Solutions</p>
      </div>
      <div className="flex flex-1 flex-col bg-bg">
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-5 py-10">
          <div className="mb-8 lg:hidden">
            <Logo size={44} />
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-navy">{t("core.login.title")}</h2>
          <p className="mb-6 text-sm text-muted">{otpChannel() === "email" ? t("core.login.subtitleEmail") : t("core.login.subtitleSms")}</p>
          <LoginForm channel={otpChannel()} />
        </div>
        <div className="lg:hidden">
          <Footer />
        </div>
      </div>
    </div>
  );
}
