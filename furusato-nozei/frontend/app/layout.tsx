import type { Metadata } from "next";
import { Shippori_Mincho, Noto_Sans_JP, DM_Mono } from "next/font/google";
import "./globals.css";

const shippori = Shippori_Mincho({
  variable: "--font-shippori",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const noto = Noto_Sans_JP({
  variable: "--font-noto",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  display: "swap",
});

const dmMono = DM_Mono({
  variable: "--font-dm-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "ふるさと納税 還元率最適化",
  description: "年収から上限額を計算し、最も還元率の高い返礼品を横断比較するツール",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="ja"
      className={`${shippori.variable} ${noto.variable} ${dmMono.variable} h-full`}
    >
      <body className="min-h-full flex flex-col font-sans" style={{ background: "var(--bg)", color: "var(--text-1)" }}>
        {children}
      </body>
    </html>
  );
}
