import Link from "next/link";

/** The Verba wordmark. Two raster variants are swapped by theme via CSS. */
export function Logo({ href = "/", height = 22, label = "Verba" }: { href?: string; height?: number; label?: string }) {
  const width = Math.round((height * 1174) / 227);
  return (
    <Link href={href} className="logo" aria-label={label}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="logo-dark" src="/brand/verba-logo-dark.png" alt="" width={width} height={height} />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="logo-light" src="/brand/verba-logo-light.png" alt="" width={width} height={height} />
    </Link>
  );
}

/** The V mark alone, theme-aware. */
export function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <span className="logo-mark" style={{ width: size, height: size }} aria-hidden="true">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="logo-dark" src="/brand/verba-mark-dark.png" alt="" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="logo-light" src="/brand/verba-mark-light.png" alt="" />
    </span>
  );
}
