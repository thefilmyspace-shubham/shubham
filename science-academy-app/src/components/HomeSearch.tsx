"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search, X } from "lucide-react";
import { SEARCH_EXAMPLES } from "@/lib/search";

/**
 * The one search bar of the app (Home only): student ID (current or
 * earlier), name, parent's mobile number, or class.
 */
export function HomeSearch({ defaultValue = "", showContacts = true, autoFocus = false }: { defaultValue?: string; showContacts?: boolean; autoFocus?: boolean }) {
  const router = useRouter();
  const [q, setQ] = useState(defaultValue);
  const go = (value: string) => {
    const v = value.trim();
    if (v) router.push(`/search?q=${encodeURIComponent(v)}`);
  };
  const examples = showContacts ? SEARCH_EXAMPLES : SEARCH_EXAMPLES.filter((e) => !/^\d+$/.test(e));
  return (
    <div>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          go(q);
        }}
        className="flex items-center gap-2 rounded-card border border-line bg-card px-3 shadow-card focus-within:border-primary"
      >
        <Search size={19} className="shrink-0 text-faint" />
        <input
          type="search"
          name="q"
          value={q}
          autoFocus={autoFocus}
          onChange={(e) => setQ(e.target.value)}
          placeholder={showContacts ? "Search ID, name, parent's mobile or class" : "Search ID, name or class"}
          className="min-w-0 flex-1 bg-transparent py-3 text-[15px] outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
          aria-label="Search students"
        />
        {q && (
          <button type="button" onClick={() => setQ("")} className="text-faint" aria-label="Clear">
            <X size={17} />
          </button>
        )}
        <button className="btn btn-primary my-1.5 px-3 py-1.5 text-[13px]">Search</button>
      </form>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[12px]">
        <span className="font-semibold text-muted">Try:</span>
        {examples.map((e) => (
          <button
            key={e}
            type="button"
            onClick={() => {
              setQ(e);
              go(e);
            }}
            className="rounded-full border border-line bg-card px-2.5 py-0.5 font-semibold text-primary hover:border-primary"
          >
            {e}
          </button>
        ))}
      </div>
    </div>
  );
}
