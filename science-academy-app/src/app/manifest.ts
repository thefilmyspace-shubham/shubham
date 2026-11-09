import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Science Academy",
    short_name: "Science Academy",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#ffffff",
    // Home screen: the graduate mark (192). Opening splash: Android picks the
    // big one, which is the mark with "SCIENCE ACADEMY / We believe in quality"
    // and a line under it, all on white.
    icons: [
      { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/splash-1024.png", sizes: "1024x1024", type: "image/png", purpose: "any" },
    ],
  };
}
