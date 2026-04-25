import { getChaseCards, getChaseMovers } from "@/lib/api"
import { getUser } from "@/lib/auth"
import { ChaseCardTable } from "@/components/chase/ChaseCardTable"
import { ChaseMoversPanel } from "@/components/chase/ChaseMoversPanel"
import type { Metadata } from "next"

export const dynamic = "force-dynamic"

export const metadata: Metadata = {
  title: "Pokémon TCG Chase Card Tracker — Raw & PSA 10 Prices 2026",
  description:
    "Track raw prices, PSA 10 values and grading ROI for the top chase cards across 40+ Pokémon TCG sets. Find the best cards to grade in 2026. Updated weekly from PriceCharting.",
  keywords: [
    "pokemon chase card prices",
    "psa 10 pokemon card value 2026",
    "pokemon card grading roi",
    "best pokemon cards to grade 2026",
    "pokemon tcg singles tracker",
    "pokemon card investment tracker",
    "pokemon grading premium calculator",
    "umbreon vmax psa 10 price",
    "charizard psa 10 value",
    "pokemon tcg investment uk",
  ],
  alternates: { canonical: "https://tcginvest.uk/tools/chase-cards" },
  openGraph: {
    title: "Pokémon TCG Chase Card Tracker — Raw & PSA 10 Prices 2026",
    description:
      "Track raw prices, PSA 10 values and grading ROI for the top chase cards across 40+ Pokémon TCG sets. Updated weekly.",
    url: "https://tcginvest.uk/tools/chase-cards",
    images: [
      {
        url: "https://tcginvest.uk/og-chase-cards.png",
        width: 1200,
        height: 630,
        alt: "Pokémon TCG Chase Card Tracker — TCG Invest",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Pokémon TCG Chase Card Tracker — Raw & PSA 10 Prices 2026",
    description:
      "Track raw prices, PSA 10 values and grading ROI for the top chase cards across 40+ Pokémon TCG sets.",
    images: ["https://tcginvest.uk/og-chase-cards.png"],
  },
}

const chaseCardsJsonLd = {
  "@context": "https://schema.org",
  "@type": "Dataset",
  name: "Pokémon TCG Chase Card Price Tracker",
  description:
    "Weekly-updated dataset of raw and PSA 10 prices, grading ROI, and pull EV for top chase cards across 40+ Pokémon TCG sets. Data sourced from PriceCharting sold listings.",
  url: "https://tcginvest.uk/tools/chase-cards",
  creator: {
    "@type": "Organization",
    name: "TCG Invest",
    url: "https://tcginvest.uk",
  },
  temporalCoverage: "2025/..",
  variableMeasured: [
    "Raw card price (GBP)",
    "PSA 10 graded price (GBP)",
    "Grading ROI (GBP)",
    "Grade multiplier",
    "Pull EV per booster box",
  ],
  license: "https://tcginvest.uk/premium",
  keywords: [
    "Pokémon TCG",
    "chase cards",
    "PSA grading",
    "card investment",
    "grading ROI",
    "PriceCharting",
  ],
}

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Which Pokémon cards are worth grading in 2026?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Cards with the highest grading ROI are typically alternate art and secret rare cards from sets like Evolving Skies (Umbreon VMAX AA), Fusion Strike (Gengar VMAX AA), and Lost Origin (Giratina V AA). Use the Grade Signal column in TCG Invest's Chase Card Tracker to identify cards where PSA 10 grading is worth the cost.",
      },
    },
    {
      "@type": "Question",
      name: "What is grading ROI for Pokémon cards?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Grading ROI is the profit you make from getting a Pokémon card graded PSA 10, calculated as: PSA 10 price minus raw (ungraded) price minus grading fee. A positive grading ROI means the PSA 10 premium exceeds the cost of grading.",
      },
    },
    {
      "@type": "Question",
      name: "How often are chase card prices updated?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Prices on the TCG Invest Chase Card Tracker are updated weekly every Sunday, sourced from recent sold listings on PriceCharting.",
      },
    },
  ],
}

export default async function ChaseCardsPage() {
  const [chaseData, moversData, userData] = await Promise.allSettled([
    getChaseCards(),
    getChaseMovers(),
    getUser(),
  ])

  const data   = chaseData.status === "fulfilled" ? chaseData.value : { sets: [], grading_fee_gbp: 20 }
  const movers = moversData.status === "fulfilled" ? moversData.value : null
  const user   = userData.status === "fulfilled" && userData.value?.authenticated ? userData.value : null

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(chaseCardsJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Chase Card Tracker</h1>
          <p className="text-gray-400 text-sm max-w-2xl">
            Top cards per set ranked by current market price. Includes raw price, PSA 10 value, grading ROI
            and pull EV contribution per booster box. Updated weekly from PriceCharting sold listings.
          </p>
        </div>
        {movers && (
          <ChaseMoversPanel
            movers={movers.movers ?? []}
            latest={movers.latest}
            previous={movers.previous ?? null}
          />
        )}
        <ChaseCardTable sets={data.sets} gradingFee={data.grading_fee_gbp} user={user} />
      </main>
    </>
  )
}
