"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, BookOpen, BriefcaseBusiness, Crown, Headset, LoaderCircle, Users } from "lucide-react";
import type { DictKey } from "@/lib/i18n";
import { useT } from "@/components/I18nProvider";
import { LanguagePicker } from "@/components/LanguagePicker";

type RoleKey = "admin" | "management" | "reception" | "faculty" | "parent";

const ROLES: { key: RoleKey; label: DictKey; hint: DictKey; icon: typeof Crown }[] = [
  { key: "parent", label: "core.login.roleParent", hint: "core.login.hintParent", icon: Users },
  { key: "faculty", label: "core.role.faculty", hint: "core.login.hintStaff", icon: BookOpen },
  { key: "reception", label: "core.role.reception", hint: "core.login.hintStaff", icon: Headset },
  { key: "management", label: "core.role.management", hint: "core.login.hintStaff", icon: BriefcaseBusiness },
  { key: "admin", label: "core.role.admin", hint: "core.login.hintStaff", icon: Crown },
];

const RESEND_SECONDS = 30;

export function LoginForm({ channel }: { channel: "email" | "sms" }) {
  const router = useRouter();
  const t = useT();
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
    const timer = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(timer);
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
        setError(data.error ?? t("core.login.couldNotSend"));
        if (data.retryAfter) setWait(data.retryAfter);
        return;
      }
      setChallenge(data.challenge);
      setMasked(data.sentTo);
      setDevCode(data.devCode ?? null);
      setCode("");
      setStep("otp");
      setWait(RESEND_SECONDS);
    } catch {
      setError(t("core.login.noInternet"));
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
        setError(data.error ?? t("core.login.wrongCode"));
        setBusy(false);
        return;
      }
      router.replace(data.home);
      router.refresh();
    } catch {
      setError(t("core.login.noInternet"));
      setBusy(false);
    }
  }

  if (step === "role") {
    return (
      <div className="space-y-2.5">
        <div className="mb-4">
          <LanguagePicker />
        </div>
        <p className="text-sm font-semibold text-muted">{t("core.login.iAm")}</p>
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
              <span className="block font-bold text-navy">{t(r.label)}</span>
              <span className="block text-xs text-muted">{t(r.hint)}</span>
            </span>
            <ArrowRight size={18} className="text-faint" />
          </button>
        ))}
      </div>
    );
  }

  if (step === "id") {
    const parent = role === "parent";
    const sms = channel === "sms";
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="space-y-4"
      >
        <button type="button" onClick={() => setStep("role")} className="flex items-center gap-1 text-sm font-bold text-primary">
          <ArrowLeft size={16} /> {roleInfo ? t(roleInfo.label) : ""}
        </button>
        <div>
          <label className="label" htmlFor="identifier">
            {sms ? (parent ? t("core.login.labelParentSms") : t("core.login.labelStaffSms")) : parent ? t("core.login.labelParent") : t("core.login.labelStaff")}
          </label>
          <input
            id="identifier"
            className="field text-[16px]"
            autoFocus
            inputMode={parent && sms ? "numeric" : "email"}
            autoComplete={parent && sms ? "tel-national" : parent ? "email" : "username"}
            placeholder={
              sms ? (parent ? t("core.login.placeholderParentSms") : t("core.login.placeholderStaffSms")) : parent ? t("core.login.placeholderParent") : t("core.login.placeholderStaff")
            }
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
          />
          {parent ? (
            <p className="mt-1.5 text-xs text-muted">
              {t("core.login.helpParent")}
              {channel === "email" ? ` ${t("core.login.helpParentEmail")}` : ""}
            </p>
          ) : (
            <p className="mt-1.5 text-xs text-muted">
              {channel === "email" ? t("core.login.helpStaffEmail") : t("core.login.helpStaffSms")}
            </p>
          )}
        </div>
        {error && <p className="text-sm font-semibold text-danger">{error}</p>}
        <button className="btn btn-primary w-full py-3" disabled={busy || identifier.trim().length < 3 || wait > 0}>
          {busy ? <LoaderCircle size={18} className="animate-spin" /> : null}
          {wait > 0 ? t("core.login.sendIn", { s: wait }) : t("core.login.sendOtp")}
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
          {channel === "email" ? t("core.login.sentEmail") : t("core.login.sentSms")} <span className="font-bold text-fg">{masked}</span>
        </p>
        <button
          type="button"
          onClick={() => {
            setStep("id");
            setError(null);
          }}
          className="mt-1 text-sm font-bold text-primary"
        >
          {t("core.login.wrongNumber")}
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
      {channel === "email" && <p className="-mt-2 text-xs text-muted">{t("core.login.checkSpam")}</p>}
      {devCode && (
        <p className="rounded-field bg-warn-soft px-3 py-2 text-xs font-semibold text-warn">
          {t("core.login.devMode", { code: devCode })}
        </p>
      )}
      {error && <p className="text-sm font-semibold text-danger">{error}</p>}
      <button className="btn btn-primary w-full py-3" disabled={busy || code.length !== 6}>
        {busy ? <LoaderCircle size={18} className="animate-spin" /> : null}
        {t("core.login.verify")}
      </button>
      <p className="text-center text-sm text-muted">
        {wait > 0 ? (
          <>{t("core.login.resendIn", { s: wait })}</>
        ) : (
          <button type="button" onClick={() => void send()} className="font-bold text-primary" disabled={busy}>
            {t("core.login.resend")}
          </button>
        )}
      </p>
      <p className="text-center text-xs text-faint">{t("core.login.stayLoggedIn")}</p>
    </form>
  );
}
