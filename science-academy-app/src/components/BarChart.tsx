/**
 * Small server-rendered bar chart (no chart library): six-month collection,
 * attendance by month and similar. Values are drawn relative to `max`.
 */
export function BarChart({
  data,
  max,
  format = (v) => String(v),
  color = "var(--color-primary)",
  highlightLast = true,
  height = 140,
}: {
  data: { label: string; value: number }[];
  max?: number;
  format?: (v: number) => string;
  color?: string;
  highlightLast?: boolean;
  height?: number;
}) {
  const top = Math.max(max ?? 0, ...data.map((d) => d.value), 1);
  return (
    <div className="flex items-end gap-2" style={{ height }} role="img" aria-label={data.map((d) => `${d.label}: ${format(d.value)}`).join(", ")}>
      {data.map((d, i) => {
        const h = Math.max(2, Math.round((d.value / top) * (height - 38)));
        const last = highlightLast && i === data.length - 1;
        return (
          <div key={d.label + i} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1">
            <span className="text-[10.5px] font-bold whitespace-nowrap text-muted">{format(d.value)}</span>
            <div className="w-full max-w-10 rounded-t-md" style={{ height: h, background: color, opacity: last ? 1 : 0.55 }} />
            <span className="text-[11px] font-semibold text-muted">{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Horizontal progress bar. */
export function Meter({ value, max = 100, tone = "primary" }: { value: number; max?: number; tone?: "primary" | "ok" | "danger" | "warn" }) {
  const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100));
  const bg = { primary: "bg-primary", ok: "bg-green", danger: "bg-danger", warn: "bg-warn" }[tone];
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-field">
      <div className={`h-full rounded-full ${bg}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
