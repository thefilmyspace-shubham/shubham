import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Science Academy",
    short_name: "Science Academy",
    start_url: "/",
    display: "standalone",
    background_color: "#f3f5f9",
    theme_color: "#0b3c5d",
    icons: [
      { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
