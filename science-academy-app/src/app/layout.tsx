import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { getLang } from "@/lib/i18n/server";
import { htmlLang } from "@/lib/i18n";
import { I18nProvider } from "@/components/I18nProvider";
import "./globals.css";

const inter = localFont({
  src: [
    { path: "./fonts/inter-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/inter-latin-500-normal.woff2", weight: "500" },
    { path: "./fonts/inter-latin-700-normal.woff2", weight: "700" },
    { path: "./fonts/inter-latin-800-normal.woff2", weight: "800" },
  ],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Science Academy", template: "%s · Science Academy" },
  description: "Science Academy, Ratlam: students, fees, attendance, tests and parent updates in one place.",
  applicationName: "Science Academy",
  appleWebApp: { capable: true, title: "Science Academy", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#ffffff",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const lang = await getLang();
  return (
    <html lang={htmlLang(lang)} className={inter.variable}>
      <body className="min-h-dvh font-sans antialiased">
        <I18nProvider lang={lang}>{children}</I18nProvider>
      </body>
    </html>
  );
}
