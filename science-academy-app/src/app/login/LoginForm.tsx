"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, BookOpen, BriefcaseBusiness, Crown, Headset, LoaderCircle, Users } from "lucide-react";

type RoleKey = "admin" | "management" | "reception" | "faculty" | "parent";

const ROLES: { key: RoleKey; label: string; hint: string; icon: typeof Crown }[] = [
  { key: "parent", label: "Parent / Guardian", hint: "Login number of your child", icon: Users },
  { key: "faculty", label: "Faculty", hint: "FC-01 or mobile", icon: BookOpen },
  { key: "reception", label: "Reception", hint: "RC-01 or mobile", icon: Headset },
  { key: "management", label: "Management", hint: "MG-01 or mobile", icon: BriefcaseBusiness },
  { key: "admin", label: "Admin", hint: "AD-01 or mobile", icon: Crown },
];

const RESEND_SECONDS = 30;

export function LoginForm() {
  const router = useRouter();
  const [step, setStep] = useState<"role" | "id" | "otp">("role");
  const [role, setRole] = useState<RoleKey | null>(null);
  const [identifier, setIdentifier] = useState("");
  const [challenge, setChallenge] = useState("");
  const [masked, setMasked] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wait, setWait] = useState(0);
  const codeRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  useEffect(() => {
    if (step === "otp") codeRef.current?.focus();
  }, [step]);

  const roleInfo = ROLES.find((r) => r.key === role);

  async function send() {
    if (!role) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/send", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ role, identifier }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Could not send the code.");
        if (data.retryAfter) setWait(data.retryAfter);
        return;
      }
      setChallenge(data.challenge);
      setMasked(data.maskedMobile);
      setDevCode(data.devCode ?? null);
      setCode("");
      setStep("otp");
      setWait(RESEND_SECONDS);
    } catch {
      setError("No internet. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function verify(value = code) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ challenge, code: value }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Wrong code.");
        setBusy(false);
        return;
      }
      router.replace(data.home);
      router.refresh();
    } catch {
      setError("No internet. Please try again.");
      setBusy(false);
    }
  }

  if (step === "role") {
    return (
      <div className="space-y-2.5">
        <p className="text-sm font-semibold text-muted">I am a…</p>
        {ROLES.map((r) => (
          <button
            key={r.key}
            onClick={() => {
              setRole(r.key);
              setError(null);
              setStep("id");
            }}
            className="flex w-full items-center gap-3 rounded-card border border-line bg-card px-4 py-3 text-left hover:border-primary"
          >
            <span className="grid h-10 w-10 place-items-center rounded-full bg-primary-soft text-primary">
              <r.icon size={19} />
            </span>
            <span className="flex-1">
              <span className="block font-bold text-navy">{r.label}</span>
              <span className="block text-xs text-muted">{r.hint}</span>
            </span>
            <ArrowRight size={18} className="text-faint" />
          </button>
        ))}
      </div>
    );
  }

  if (step === "id") {
    const parent = role === "parent";
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="space-y-4"
      >
        <button type="button" onClick={() => setStep("role")} className="flex items-center gap-1 text-sm font-bold text-primary">
          <ArrowLeft size={16} /> {roleInfo?.label}
        </button>
        <div>
          <label className="label" htmlFor="identifier">
            {parent ? "Registered mobile number" : "Staff ID or registered mobile"}
          </label>
          <div className="flex items-center gap-2">
            {parent && <span className="rounded-field border border-line bg-field px-3 py-2.5 text-[15px] font-semibold text-muted">+91</span>}
            <input
              id="identifier"
              className="field text-[16px]"
              autoFocus
              inputMode={parent ? "numeric" : "text"}
              autoComplete={parent ? "tel-national" : "username"}
              placeholder={parent ? "98765 43210" : roleInfo?.hint}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
            />
          </div>
          {parent && <p className="mt-1.5 text-xs text-muted">Use the one number the academy chose as your login number at registration.</p>}
        </div>
        {error && <p className="text-sm font-semibold text-danger">{error}</p>}
        <button className="btn btn-primary w-full py-3" disabled={busy || identifier.trim().length < 3 || wait > 0}>
          {busy ? <LoaderCircle size={18} className="animate-spin" /> : null}
          {wait > 0 ? `Send code in ${wait}s` : "Send OTP"}
        </button>
      </form>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void verify();
      }}
      className="space-y-4"
    >
      <div>
        <p className="text-sm text-muted">
          We sent a 6 digit code by SMS to <span className="font-bold text-fg">{masked}</span>
        </p>
        <button
          type="button"
          onClick={() => {
            setStep("id");
            setError(null);
          }}
          className="mt-1 text-sm font-bold text-primary"
        >
          Wrong number?
        </button>
      </div>
      <input
        ref={codeRef}
        className="field text-center text-2xl font-extrabold tracking-[0.5em]"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        placeholder="••••••"
        value={code}
        onChange={(e) => {
          const v = e.target.value.replace(/\D/g, "").slice(0, 6);
          setCode(v);
          if (v.length === 6 && !busy) void verify(v);
        }}
      />
      {devCode && (
        <p className="rounded-field bg-warn-soft px-3 py-2 text-xs font-semibold text-warn">
          Development mode (no SMS set up): your code is {devCode}
        </p>
      )}
      {error && <p className="text-sm font-semibold text-danger">{error}</p>}
      <button className="btn btn-primary w-full py-3" disabled={busy || code.length !== 6}>
        {busy ? <LoaderCircle size={18} className="animate-spin" /> : null}
        Verify and log in
      </button>
      <p className="text-center text-sm text-muted">
        {wait > 0 ? (
          <>Resend code in {wait}s</>
        ) : (
          <button type="button" onClick={() => void send()} className="font-bold text-primary" disabled={busy}>
            Resend OTP
          </button>
        )}
      </p>
      <p className="text-center text-xs text-faint">You stay logged in on this device until you press Log out.</p>
    </form>
  );
}
