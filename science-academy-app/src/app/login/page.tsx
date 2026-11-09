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
      <div className="hidden flex-1 flex-col justify-between bg-navy p-10 text-white lg:flex">
        <div className="w-fit rounded-card bg-white px-4 py-3">
          <Logo size={44} />
        </div>
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight">Ratlam&apos;s science coaching, run in one app.</h1>
          <p className="mt-3 max-w-md text-white/70">Students, fees, bills, attendance, timetable, tests, ranks and parent updates for classes 6 to 12, CBSE and MP Board.</p>
        </div>
        <p className="text-sm text-white/50">Powered by TFS · The First Solutions</p>
      </div>
      <div className="flex flex-1 flex-col">
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
