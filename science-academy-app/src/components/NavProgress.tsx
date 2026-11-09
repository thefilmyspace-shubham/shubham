"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";

/**
 * A thin bar at the top of the screen from the moment a link is tapped until
 * the next page is on screen, so every tap visibly does something even on a
 * slow network.
 */
export function NavProgress() {
  const pathname = usePathname();
  const search = useSearchParams();
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const safety = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const start = () => {
      setState("busy");
      if (safety.current) clearTimeout(safety.current);
      // Never spin for ever (a download link, a form that stays on the page).
      safety.current = setTimeout(() => setState("done"), 12_000);
    };
    // Capture phase: Next's <Link> cancels the browser's own navigation, so
    // looking later would see every link click as cancelled.
    const onClick = (e: MouseEvent) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as HTMLElement | null)?.closest?.("a");
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      const href = a.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return;
      const url = new URL(href, location.href);
      if (url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
      if (url.pathname === location.pathname && url.search === location.search) return;
      start();
    };
    // Forms show their own spinner on the button (SubmitButton).
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, []);

  // A new page (or new query) arrived: finish the bar.
  const key = `${pathname}?${search.toString()}`;
  const [lastKey, setLastKey] = useState(key);
  if (key !== lastKey) {
    setLastKey(key);
    if (state === "busy") setState("done");
  }

  useEffect(() => {
    if (state !== "done") return;
    if (safety.current) clearTimeout(safety.current);
    const t = setTimeout(() => setState("idle"), 300);
    return () => clearTimeout(t);
  }, [state]);

  if (state === "idle") return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[3px]" aria-hidden>
      <div className={`h-full bg-primary shadow-[0_0_8px_var(--color-primary)] ${state === "busy" ? "nav-bar-busy" : "nav-bar-done"}`} />
    </div>
  );
}
