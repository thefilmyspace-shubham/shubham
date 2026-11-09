"use client";

import { useEffect, useState } from "react";
import { BellOff, BellRing, LoaderCircle, Smartphone, X } from "lucide-react";
import { useT } from "./I18nProvider";

// Phone notifications (web push): the popup on Home, and a setting row.

type State = "loading" | "unsupported" | "ios-install" | "ask" | "on" | "denied" | "error" | "working";

const LATER_KEY = "sa_push_later";
const LATER_DAYS = 3;

function toKey(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function standalone(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
}

async function currentState(): Promise<State> {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    return ios && !standalone() ? "ios-install" : "unsupported";
  }
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.register("/sw.js");
  const sub = await reg.pushManager.getSubscription();
  if (sub) {
    // Keep the server's copy fresh (a new login on this phone, or a cleared list).
    void save(sub);
    return "on";
  }
  if (Notification.permission === "granted") return (await subscribe()) ? "on" : "error";
  return "ask";
}

async function save(sub: PushSubscription): Promise<boolean> {
  const res = await fetch("/api/push/subscribe", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(sub.toJSON()) });
  return res.ok;
}

async function subscribe(): Promise<boolean> {
  const keyRes = await fetch("/api/push/key");
  if (!keyRes.ok) return false;
  const { publicKey } = (await keyRes.json()) as { publicKey: string };
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  const sub = (await reg.pushManager.getSubscription()) ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toKey(publicKey) }));
  return save(sub);
}

async function turnOn(): Promise<State> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return permission === "denied" ? "denied" : "ask";
  return (await subscribe()) ? "on" : "error";
}

function usePush() {
  const [state, setState] = useState<State>("loading");
  useEffect(() => {
    currentState()
      .then(setState)
      .catch(() => setState("error"));
  }, []);
  const enable = async () => {
    setState("working");
    try {
      setState(await turnOn());
    } catch {
      setState("error");
    }
  };
  return { state, enable };
}

/** Home: a popup asking to turn on phone notifications (until on, or "Later" for 3 days). */
export function PushPrompt() {
  const t = useT();
  const { state, enable } = usePush();
  const [hidden, setHidden] = useState(true);

  useEffect(() => {
    let later = 0;
    try {
      later = Number(localStorage.getItem(LATER_KEY) || 0);
    } catch {
      later = 0;
    }
    const timer = setTimeout(() => setHidden(Date.now() - later < LATER_DAYS * 86_400_000), 0);
    return () => clearTimeout(timer);
  }, []);

  if (hidden || !(state === "ask" || state === "working" || state === "ios-install" || state === "error")) return null;
  const later = () => {
    try {
      localStorage.setItem(LATER_KEY, String(Date.now()));
    } catch {
      /* private mode: the popup just shows again next time */
    }
    setHidden(true);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/35 p-3 sm:items-center" role="presentation" onClick={later}>
      <div
        role="dialog"
        aria-labelledby="push-title"
        onClick={(e) => e.stopPropagation()}
        className="safe-bottom w-full max-w-sm rounded-3xl bg-card p-5 shadow-sheet"
      >
        <div className="flex items-start gap-3">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-primary-soft text-primary">
            {state === "ios-install" ? <Smartphone size={22} /> : <BellRing size={22} />}
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="push-title" className="text-[17px] font-extrabold text-navy">
              {t("core.push.title")}
            </h2>
            <p className="mt-1 text-[14px] text-muted">{state === "ios-install" ? t("core.push.iosInstall") : t("core.push.body")}</p>
          </div>
          <button type="button" onClick={later} className="-mt-1 -mr-1 grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-field" aria-label={t("core.close")}>
            <X size={18} />
          </button>
        </div>
        {state === "error" && <p className="mt-3 text-[13px] font-semibold text-danger">{t("core.push.error")}</p>}
        <div className="mt-4 flex gap-2">
          <button type="button" onClick={later} className="btn btn-ghost flex-1">
            {t("core.push.later")}
          </button>
          {state !== "ios-install" && (
            <button type="button" onClick={() => void enable()} className="btn btn-primary flex-1" disabled={state === "working"}>
              {state === "working" ? <LoaderCircle size={16} className="animate-spin" /> : <BellRing size={16} />} {t("core.push.turnOn")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/** A settings row: shows whether phone notifications are on, with a button to turn them on. */
export function PushSetting() {
  const t = useT();
  const { state, enable } = usePush();
  if (state === "loading") return null;
  const row = "flex items-center gap-3 rounded-card bg-card p-4 text-sm shadow-card";
  if (state === "on")
    return (
      <p className={`${row} font-semibold text-ok`}>
        <BellRing size={18} className="shrink-0" /> {t("core.push.enabled")}
      </p>
    );
  if (state === "denied")
    return (
      <p className={`${row} text-warn`}>
        <BellOff size={18} className="shrink-0" /> {t("core.push.denied")}
      </p>
    );
  if (state === "ios-install" || state === "unsupported")
    return (
      <p className={`${row} text-muted`}>
        <Smartphone size={18} className="shrink-0" /> {state === "ios-install" ? t("core.push.iosInstall") : t("core.push.unsupported")}
      </p>
    );
  return (
    <div className={row}>
      <BellOff size={18} className="shrink-0 text-muted" />
      <span className="min-w-0 flex-1">{state === "error" ? t("core.push.error") : t("core.push.off")}</span>
      <button type="button" className="btn btn-primary py-1.5 text-[13px]" onClick={() => void enable()} disabled={state === "working"}>
        {state === "working" ? <LoaderCircle size={15} className="animate-spin" /> : null} {t("core.push.turnOn")}
      </button>
    </div>
  );
}
