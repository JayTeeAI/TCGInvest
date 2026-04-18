import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Upgrade to Premium — TCG Invest",
  description:
    "Unlock full Pokemon TCG investment analysis for £3/month. Get AI buy/sell recommendations, unlimited watchlist, PSA grading premiums, score breakdowns and price alerts.",
  alternates: {
    canonical: "https://tcginvest.uk/premium",
  },
  openGraph: {
    title: "Upgrade to TCG Invest Premium — £3/month",
    description:
      "Unlock AI investment scores, unlimited watchlist, PSA grading analysis and price alerts for Pokemon TCG sealed products.",
    url: "https://tcginvest.uk/premium",
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function PremiumLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
