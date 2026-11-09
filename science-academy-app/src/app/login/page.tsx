import { redirect } from "next/navigation";
import { getViewer, homeFor } from "@/lib/auth";
import { Logo } from "@/components/Logo";
import { Footer } from "@/components/ui";
import { otpChannel } from "@/lib/env";
import { LoginForm } from "./LoginForm";

export const metadata = { title: "Log in" };

export default async function LoginPage() {
  const viewer = await getViewer().catch(() => null);
  if (viewer) redirect(homeFor(viewer));
  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden border-r border-line bg-card p-10 lg:flex">
        <div className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-navy via-primary to-green" />
        <Logo size={72} />
        <div className="max-w-lg">
          <p className="text-sm font-bold tracking-widest text-green uppercase">We believe in quality</p>
          <h1 className="mt-3 text-4xl leading-tight font-extrabold tracking-tight text-navy">
            Strong basics today,
            <br />
            bright results tomorrow.
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-muted">
            Science Academy, Ratlam guides students of classes 6 to 12, CBSE and MP Board, with clear concepts, regular tests and
            personal attention, so every child learns with confidence and every parent stays informed.
          </p>
          <ul className="mt-6 flex flex-wrap gap-2 text-[13px] font-semibold">
            {["Classes 6 to 12", "CBSE & MP Board", "Regular tests & ranks", "Parents stay updated"].map((t) => (
              <li key={t} className="rounded-full bg-primary-soft px-3 py-1.5 text-primary">
                {t}
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
          <h2 className="text-2xl font-extrabold tracking-tight text-navy">Log in</h2>
          <p className="mb-6 text-sm text-muted">One time code by {otpChannel() === "email" ? "email" : "SMS"}. No password.</p>
          <LoginForm channel={otpChannel()} />
        </div>
        <div className="lg:hidden">
          <Footer />
        </div>
      </div>
    </div>
  );
}
