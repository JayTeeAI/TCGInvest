import { getSets, getSummary, getMovers, getRunDates, getHeatScores } from "@/lib/api"
import { TrackerTable } from "@/components/tracker/TrackerTable"
import { SummaryCards } from "@/components/tracker/SummaryCards"
import { MoversPanel } from "@/components/tracker/MoversPanel"
import Link from "next/link"
import { Disclaimer } from "@/components/Disclaimer"
import { DatePickerDropdown } from "@/components/tracker/DatePickerDropdown"
import { getUser } from "@/lib/auth"
import type { Metadata } from "next"

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: "Pokémon Booster Box Tracker — Monthly Price & Investment Scores 2026",
  description:
    "Track Pokémon TCG booster box prices and AI investment scores across 44+ sets. See buy signals, strong buys, and monthly price trends. Free tool, updated monthly.",
  keywords: [
    "pokemon booster box tracker",
    "best booster boxes to hold 2026",
    "pokemon tcg price tracker",
    "pokemon sealed investment scores",
    "pokemon card market trends 2026",
    "booster box investment",
  ],
  alternates: {
    canonical: "https://tcginvest.uk/tools/tracker",
  },
  openGraph: {
    title: "Pokémon Booster Box Tracker — Monthly Price & Investment Scores 2026",
    description:
      "Track Pokémon TCG booster box prices and AI investment scores across 44+ sets. Free monthly data.",
    url: "https://tcginvest.uk/tools/tracker",
    images: [
      {
        url: "/og-tracker.png",
        width: 1200,
        height: 630,
        alt: "Pokémon TCG Booster Box Investment Tracker",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Pokémon Booster Box Tracker — Monthly Investment Scores",
    description:
      "AI-powered investment scores across 44+ Pokémon TCG sealed sets. Free monthly tracker.",
    images: ["/og-tracker.png"],
  },
}

export default async function TrackerPage({
  searchParams,
}: {
  searchParams: Promise<{ month?: string }>
}) {
  const params = await searchParams
  const selectedMonth = params.month || undefined

  const [setsData, summaryData, moversData, datesData, userData] = await Promise.allSettled([
    getSets({ run_date: selectedMonth }),
    getSummary(),
    getMovers(),
    getRunDates(),
    getUser(),
  ])

  const sets      = setsData.status === "fulfilled"    ? setsData.value.sets       : []
  const runDate   = setsData.status === "fulfilled"    ? setsData.value.run_date   : null
  const summary   = summaryData.status === "fulfilled" ? summaryData.value         : null
  const movers    = moversData.status === "fulfilled"  ? moversData.value          : null
  const runDates  = datesData.status === "fulfilled"   ? datesData.value.run_dates : []
  const user      = userData.status === "fulfilled" && userData.value.authenticated ? userData.value : null
  const isPremiumUser = user?.role === "premium" || user?.role === "admin"
  const heatScores = isPremiumUser ? await getHeatScores().catch(() => ({})) : {}

  const trackerJsonLd = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: "Pokémon TCG Booster Box Investment Tracker",
    description: `Monthly Pokémon TCG booster box prices and AI investment scores across ${sets.length} sets. Includes buy signals, price trends, and set value analysis.`,
    url: "https://tcginvest.uk/tools/tracker",
    creator: {
      "@type": "Organization",
      name: "TCG Invest",
      url: "https://tcginvest.uk",
    },
    temporalCoverage: "2024/..",
    spatialCoverage: "GB",
    variableMeasured: [
      "Booster Box Price GBP",
      "Set Value GBP",
      "Box Percentage",
      "Chase Percentage",
      "Investment Score",
    ],
    keywords: [
      "Pokemon TCG",
      "booster box prices",
      "sealed product investment",
      "trading card investment",
    ],
  }

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "What is the best Pokémon booster box to hold in 2026?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Our AI investment scores analyse scarcity, liquidity, mascot power, and set depth to identify strong buy opportunities. Sign in free to see the full ranked list with buy and strong buy signals.",
        },
      },
      {
        "@type": "Question",
        name: "How is the Pokémon TCG investment score calculated?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Each set is scored out of 20 across four dimensions: Scarcity (print run and availability), Liquidity (trading volume), Mascot Power (desirability of featured Pokémon), and Set Depth (overall card quality). Scores are generated monthly using Groq AI.",
        },
      },
      {
        "@type": "Question",
        name: "What does Box % mean on the tracker?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Box % is the booster box price divided by the total set value. A lower Box % means you are paying less for the sealed product relative to the value of cards inside — generally a better investment entry point.",
        },
      },
    ],
  }

  const fmtDate = (d: string) => {
    const [y, m] = d.split("-")
    const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return `${months[parseInt(m)]} '${y.slice(2)}`
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(trackerJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <main className="min-h-screen bg-slate-950 text-slate-100">
        <div className="max-w-7xl mx-auto px-6 py-12">

          <div className="mb-8">
            <Link href="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
              ← Back to tools
            </Link>
          </div>

          <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">Pokémon Booster Box Tracker</h1>
              <p className="text-slate-400">
                Monthly investment scores across {sets.length} Pokémon TCG sets.
                {runDate && (
                  <span className="ml-2 text-slate-500 text-sm">Showing {fmtDate(runDate)}</span>
                )}
              </p>
            </div>

            <DatePickerDropdown
              runDates={runDates}
              selectedMonth={selectedMonth}
              isPremium={isPremiumUser}
              isLoggedIn={!!user}
            />
          </div>

          {!user && (
            <div className="mb-6 bg-slate-900 border border-slate-700 rounded-xl px-5 py-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-slate-200 text-sm font-medium">Get more from the tracker</p>
                <p className="text-slate-500 text-xs mt-0.5">Sign in free to unlock historical months, set detail analysis, and your personal watchlist</p>
              </div>
              <a
                href="/auth/google"
                className="bg-white text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors whitespace-nowrap"
              >
                Sign in free →
              </a>
            </div>
          )}

          {user && user.role === "free" && (
            <div className="mb-6 bg-slate-900 border border-yellow-500/20 rounded-xl px-5 py-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-slate-200 text-sm font-medium">⭐ Unlock Premium</p>
                <p className="text-slate-500 text-xs mt-0.5">Unlimited watchlist, full score breakdowns, and price alerts for £3/month</p>
              </div>
              <a
                href="/premium"
                className="bg-yellow-500 text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-yellow-400 transition-colors whitespace-nowrap"
              >
                Upgrade →
              </a>
            </div>
          )}

          <Disclaimer />
          {summary?.stats && <SummaryCards stats={summary.stats} user={user} />}

          {movers && !selectedMonth && movers.movers?.length > 0 && user && (
            <div className="mt-8">
              <MoversPanel
                movers={movers.movers}
                latest={movers.latest}
                previous={movers.previous}
              />
            </div>
          )}

          {!user && (
            <div className="mt-6 flex items-center gap-3 px-4 py-3 bg-slate-900/50 border border-slate-800 rounded-xl">
              <span className="text-slate-400 text-sm">Weekly price movers available with a free account</span>
              <a href="/auth/google" className="text-blue-400 text-sm font-medium hover:text-blue-300 whitespace-nowrap ml-auto">Sign in free →</a>
            </div>
          )}

          <div className="mt-8">
            {sets.length > 0 ? (
              <TrackerTable sets={sets} user={user} heatScores={heatScores} />
            ) : (
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-12 text-center">
                <p className="text-slate-400">No data yet — the tracker runs on the 1st of each month.</p>
              </div>
            )}
          </div>

          <p className="text-slate-600 text-xs mt-8">
            Box % = Booster Box price ÷ Set value. Lower is better.
            Chase % = Top 3 card value ÷ Set value.
            Decision Score = Scarcity + Liquidity + Mascot Power + Set Depth (max 20).
            TCG Invest is not affiliated with The Pokémon Company International.
          </p>
        </div>
      </main>
    </>
  )
}
