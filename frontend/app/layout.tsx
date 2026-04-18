import type { Metadata } from "next"
import { Geist } from "next/font/google"
import "./globals.css"
import Header from "@/components/Header"

const geist = Geist({ subsets: ["latin"] })

export const metadata: Metadata = {
  metadataBase: new URL("https://tcginvest.uk"),
  title: {
    default: "TCG Invest — Pokémon TCG Investment Tools & Price Tracker",
    template: "%s | TCG Invest",
  },
  description:
    "Data-driven Pokémon TCG investment tools. Monthly booster box price tracking, AI investment scores, and ETB analysis across 44+ sets. Free to use.",
  keywords: [
    "pokemon tcg investment",
    "booster box tracker",
    "pokemon card price tracker",
    "best booster boxes to hold",
    "pokemon tcg market trends 2026",
    "etb investment tracker",
    "sealed pokemon investment",
  ],
  authors: [{ name: "TCG Invest" }],
  verification: {
    google: "eQIJ2gA6zIxvMHGnbTkpVOxjD1QNIlxW0-FBLDMzBNs",
  },
  creator: "TCG Invest",
  publisher: "TCG Invest",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_GB",
    url: "https://tcginvest.uk",
    siteName: "TCG Invest",
    title: "TCG Invest — Pokémon TCG Investment Tools & Price Tracker",
    description:
      "Data-driven Pokémon TCG investment tools. Monthly booster box price tracking, AI investment scores, and ETB analysis across 44+ sets.",
    images: [
      {
        url: "/og-default.png",
        width: 1200,
        height: 630,
        alt: "TCG Invest — Pokémon TCG Investment Tools",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "TCG Invest — Pokémon TCG Investment Tools",
    description:
      "Monthly booster box price tracking and AI investment scores across 44+ Pokémon TCG sets.",
    images: ["/og-default.png"],
  },
  alternates: {
    canonical: "https://tcginvest.uk",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${geist.className} bg-slate-950 antialiased`}>
        <Header />
        {children}
      </body>
    </html>
  )
}
