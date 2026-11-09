import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Science Academy",
    short_name: "Science Academy",
    start_url: "/",
    display: "standalone",
    background_color: "#f3f5f9",
    theme_color: "#13265c",
    icons: [{ src: "/brand/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
