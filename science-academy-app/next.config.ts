import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Every screen is per-user and live, so pages render on each request.
  cacheComponents: false,
  experimental: {
    staleTimes: { dynamic: 20, static: 180 },
    serverActions: { bodySizeLimit: "12mb" },
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  serverExternalPackages: ["exceljs", "jspdf", "web-push"],
  async headers() {
    return [
      {
        // A new service worker must reach phones at once.
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
        ],
      },
    ];
  },
};

export default nextConfig;
