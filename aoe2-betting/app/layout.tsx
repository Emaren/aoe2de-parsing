import type { Metadata } from "next";
import "./globals.css";
import PWARegister from "@/app/pwa";

export const metadata: Metadata = {
  title: "AoE2 Betting",
  description: "Bet on AoE2 games",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="AoE2 Betting" />
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      {/* Removed `h-screen` and `justify-center` to allow scrolling */}
      <body className="bg-gray-900 text-white">
        <PWARegister />
        {children}
      </body>
    </html>
  );
}
