import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "BCN LearnDNA — Ölçme ve Değerlendirme", description: "BCN College öğrenme zekâsı platformu" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
