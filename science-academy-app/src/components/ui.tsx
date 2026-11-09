import Link from "next/link";
import { ChevronLeft, type LucideIcon } from "lucide-react";

/**
 * Page header. On phones it sticks to the top; on desktop it is the page title.
 * (The search bar lives only on Home, per the spec.)
 */
export function PageHeader({
  title,
  subtitle,
  back,
  right,
}: {
  title: string;
  subtitle?: React.ReactNode;
  back?: string;
  right?: React.ReactNode;
}) {
  return (
    <header className="safe-top no-print sticky top-0 z-10 bg-card/95 shadow-bar backdrop-blur lg:static lg:bg-transparent lg:shadow-none">
      <div className="flex min-h-14 items-center gap-2 px-4 py-2.5 lg:px-8 lg:pt-7 lg:pb-2">
        {back && (
          <Link href={back} className="-ml-2 grid h-9 w-9 place-items-center rounded-full text-primary hover:bg-field" aria-label="Back">
            <ChevronLeft size={26} />
          </Link>
        )}
        <div className="min-w-0 flex-1">
          <h1 className={`truncate font-extrabold tracking-tight text-navy ${back ? "text-lg lg:text-2xl" : "text-[22px] lg:text-[28px]"}`}>{title}</h1>
          {subtitle && <div className="truncate text-xs text-muted lg:text-sm">{subtitle}</div>}
        </div>
        {right && <div className="flex shrink-0 items-center gap-2">{right}</div>}
      </div>
    </header>
  );
}

/** Page body: phone padding, wider on desktop. */
export function Page({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return <div className={`mx-auto w-full px-4 pt-3 pb-6 lg:px-8 ${wide ? "max-w-7xl" : "max-w-5xl"}`}>{children}</div>;
}

export function Section({
  title,
  action,
  children,
  className = "",
}: {
  title: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`pt-5 ${className}`}>
      <div className="mb-2.5 flex items-baseline justify-between gap-2">
        <h2 className="text-[15px] font-bold text-navy">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function SectionLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-[13px] font-bold text-primary">
      {children}
    </Link>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-card bg-card shadow-card ${className}`}>{children}</div>;
}

export function Empty({ children, icon: Icon }: { children: React.ReactNode; icon?: LucideIcon }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-card border border-dashed border-line bg-card px-4 py-6 text-center text-sm text-muted">
      {Icon && <Icon size={22} className="text-faint" />}
      <div>{children}</div>
    </div>
  );
}

export type Tone = "neutral" | "primary" | "danger" | "ok" | "warn" | "navy" | "violet";

const TONES: Record<Tone, string> = {
  neutral: "bg-field text-muted",
  primary: "bg-primary-soft text-primary",
  danger: "bg-danger-soft text-danger",
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  navy: "bg-navy-soft text-navy",
  violet: "bg-violet-soft text-violet",
};

/** Coloured pill. */
export function Chip({ tone = "neutral", children, className = "" }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 text-[11.5px] font-bold whitespace-nowrap ${TONES[tone]} ${className}`}>
      {children}
    </span>
  );
}

/** A number tile for dashboards. */
export function Stat({
  label,
  value,
  hint,
  tone = "navy",
  href,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  tone?: "navy" | "primary" | "ok" | "danger" | "warn";
  href?: string;
}) {
  const color = { navy: "text-navy", primary: "text-primary", ok: "text-ok", danger: "text-danger", warn: "text-warn" }[tone];
  const body = (
    <Card className="h-full p-4">
      <p className="text-xs font-semibold text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-extrabold tracking-tight ${color}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </Card>
  );
  return href ? (
    <Link href={href} className="block">
      {body}
    </Link>
  ) : (
    body
  );
}

/** A coloured info strip (e.g. "Faculty see this page without contact numbers and fees"). */
export function Banner({ tone = "primary", icon: Icon, children }: { tone?: Tone; icon?: LucideIcon; children: React.ReactNode }) {
  return (
    <div className={`flex items-start gap-2 rounded-field px-3 py-2.5 text-[13px] font-medium ${TONES[tone]}`}>
      {Icon && <Icon size={16} className="mt-0.5 shrink-0" />}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Segmented filter links: All · Paid · Partial ... with counts. */
export function FilterChips({
  items,
}: {
  items: { href: string; label: string; count?: number; active: boolean }[];
}) {
  return (
    <div className="no-print -mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-wrap lg:px-0">
      {items.map((i) => (
        <Link
          key={i.href}
          href={i.href}
          scroll={false}
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-bold ${
            i.active ? "border-primary bg-primary text-white" : "border-line bg-card text-fg hover:border-primary"
          }`}
        >
          {i.label}
          {i.count !== undefined && (
            <span className={`rounded-full px-1.5 text-[11px] ${i.active ? "bg-white/20" : "bg-field text-muted"}`}>{i.count}</span>
          )}
        </Link>
      ))}
    </div>
  );
}

/** Simple responsive table: cards on phones are left to each page; this is the desktop table look. */
export function Table({ head, children }: { head: React.ReactNode[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-card bg-card shadow-card">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-xs text-muted">
            {head.map((h, i) => (
              <th key={i} className="px-4 py-2.5 font-semibold whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}

export function Td({ children, className = "" }: { children?: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-2.5 align-middle ${className}`}>{children}</td>;
}

/** "Powered by TFS · The First Solutions" on every screen. */
export function Footer() {
  return (
    <footer className="no-print px-4 py-5 text-center text-[11.5px] font-medium text-faint">
      Powered by <span className="font-bold text-muted">TFS</span> · The First Solutions
    </footer>
  );
}
