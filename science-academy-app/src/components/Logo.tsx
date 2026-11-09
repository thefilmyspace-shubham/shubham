/* eslint-disable @next/next/no-img-element -- small static brand images, no optimisation needed */

/**
 * Science Academy logo (public/brand, cut from the owner's logo file):
 * logo.png = mark + "SCIENCE ACADEMY / WE BELIEVE IN QUALITY",
 * logo-mark.png = the graduate mark only. Both are the original artwork on its
 * own white background (no cut-out edges), so they always sit on white.
 */

const FULL_RATIO = 1821 / 417;
const MARK_RATIO = 369 / 417;

export function LogoMark({ size = 36 }: { size?: number }) {
  return (
    <img
      src="/brand/logo-mark.png"
      alt="Science Academy"
      width={Math.round(size * MARK_RATIO)}
      height={size}
      className="shrink-0 object-contain"
      style={{ height: size, width: "auto" }}
    />
  );
}

/** Full logo. `size` is its height in pixels. */
export function Logo({ size = 36 }: { size?: number; tagline?: boolean }) {
  return (
    <img
      src="/brand/logo.png"
      alt="Science Academy · We believe in quality"
      width={Math.round(size * FULL_RATIO)}
      height={size}
      className="block max-w-full shrink-0 object-contain"
      style={{ height: size, width: "auto" }}
    />
  );
}
