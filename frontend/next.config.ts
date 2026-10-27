import type { NextConfig } from "next";
import path from "node:path";

// VERBA_STATIC_EXPORT=1 builds plain files into out/ that the Python backend serves itself (Docker/hosting).
const staticExport = process.env.VERBA_STATIC_EXPORT === "1";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: { root: path.join(__dirname) },
  images: { unoptimized: true },
  ...(staticExport
    ? { output: "export" as const }
    : {
        async headers() {
          return [{ source: "/:path*", headers: securityHeaders }];
        },
      }),
};

export default nextConfig;
