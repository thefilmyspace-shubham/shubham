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
  serverExternalPackages: ["exceljs", "jspdf"],
};

export default nextConfig;
