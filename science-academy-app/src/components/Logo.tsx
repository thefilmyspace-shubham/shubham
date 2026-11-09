/**
 * Science Academy mark, drawn in the logo colours (navy, blue, green).
 * Replace with the real logo file (public/brand/logo.png) when the owner
 * sends it: set `src` below and the <img> is used instead.
 */
const LOGO_SRC: string | null = null;

export function LogoMark({ size = 36 }: { size?: number }) {
  if (LOGO_SRC) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={LOGO_SRC} alt="Science Academy" width={size} height={size} className="shrink-0 object-contain" />;
  }
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden className="shrink-0">
      <circle cx="24" cy="24" r="23" fill="#13265c" />
      <ellipse cx="24" cy="24" rx="17" ry="6.5" fill="none" stroke="#2e9b4e" strokeWidth="2.4" transform="rotate(-30 24 24)" />
      <ellipse cx="24" cy="24" rx="17" ry="6.5" fill="none" stroke="#5aa0ff" strokeWidth="2.4" transform="rotate(30 24 24)" />
      <circle cx="24" cy="24" r="4.2" fill="#ffffff" />
    </svg>
  );
}

export function Logo({ size = 36, tagline = true }: { size?: number; tagline?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark size={size} />
      <div className="leading-tight">
        <p className="text-[16px] font-extrabold tracking-tight text-navy">
          Science <span className="text-primary">Academy</span>
        </p>
        {tagline && <p className="text-[10.5px] font-semibold text-green">We believe in quality</p>}
      </div>
    </div>
  );
}
