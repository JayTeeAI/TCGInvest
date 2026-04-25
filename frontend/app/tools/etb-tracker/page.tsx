import { getETBs, getETBMovers, getETBSnapshotDates } from "@/lib/api"
import { getUser } from "@/lib/auth"
import { ETBTable } from "@/components/etb/ETBTable"
import { ETBMoversPanel } from "@/components/etb/ETBMoversPanel"
import { Disclaimer } from "@/components/Disclaimer"
import Link from "next/link"
import type { Metadata } from "next"
import { ETBJsonLd } from "@/components/etb/ETBJsonLd"

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: "Pokemon Centre ETB Tracker — Sealed Prices & PSA Premium Ratios 2026",
  description: "Track Pokemon Centre Elite Trainer Box sealed prices, promo card raw values, PSA 10 premiums and grading ratios across 27+ exclusive ETBs. Updated weekly from eBay UK sold listings.",
  keywords: ["pokemon centre etb tracker", "elite trainer box investment", "pokemon etb sealed price", "psa 10 promo card value", "pokemon centre exclusive etb"],
  alternates: { canonical: "https://tcginvest.uk/tools/etb-tracker" },
  openGraph: {
    title: "Pokemon Centre ETB Tracker — Sealed Prices & PSA Premium Ratios 2026",
    description: "Track Pokemon Centre Elite Trainer Box sealed prices, promo card values and PSA grading premiums. Weekly data from eBay UK sold listings.",
    url: "https://tcginvest.uk/tools/etb-tracker",
    images: [{ url: "/og-etb.png", width: 1200, height: 630, alt: "Pokemon Centre ETB Investment Tracker" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Pokemon Centre ETB Tracker — Sealed Prices & PSA Premiums",
    description: "Weekly Pokemon Centre ETB sealed prices, promo card values and PSA 10 grading premiums. Free tracker.",
    images: ["/og-etb.png"],
  },
}

function fmtDate(d: string) {
  const [y, m] = d.split("-")
  const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
  return `${months[parseInt(m)]} ${y}`
}

export default async function ETBTrackerPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>
}) {
  const params = await searchParams
  const selectedDate = params.date || undefined

  const [etbData, moversData, datesData, userData] = await Promise.allSettled([
    getETBs(selectedDate),
    getETBMovers(),
    getETBSnapshotDates(),
    getUser(),
  ])

  const etbs          = etbData.status === "fulfilled" ? etbData.value.etbs : []
  const movers        = moversData.status === "fulfilled" ? moversData.value : null
  const snapshotDates = datesData.status === "fulfilled" ? datesData.value.snapshot_dates : []
  const user          = userData.status === "fulfilled" && userData.value.authenticated ? userData.value : null
  const isLoggedIn    = !!user
  const isLatestDate  = !selectedDate || selectedDate === snapshotDates[0]

  return (
    <>
      <ETBJsonLd count={etbs.length} />
      <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-7xl mx-auto px-6 py-12">

        <div className="mb-8">
          <Link href="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">Back to tools</Link>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-white">Pokemon Centre ETB Tracker</h1>
              <span className="text-xs font-medium px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Updated weekly</span>
            </div>
            <p className="text-slate-400">
              Sealed prices, promo card values and PSA grading premiums for {etbs.length} Pokemon Centre exclusive ETBs.
              {selectedDate && (
                <span className="ml-2 text-slate-500 text-sm">Showing {fmtDate(selectedDate)}</span>
              )}
            </p>
          </div>

          {snapshotDates.length > 1 && (
            <div className="flex gap-2 flex-wrap">
              {snapshotDates.map((d: string, i: number) => {
                const isLatest   = i === 0
                const isSelected = (selectedDate === d) || (!selectedDate && isLatest)
                const isLocked   = !isLatest && !user

                if (isLocked) {
                  return (
                    <Link
                      key={d}
                      href="/auth/google"
                      className="px-3 py-1.5 rounded-lg text-sm transition-colors bg-slate-900 text-slate-600 border border-slate-800 flex items-center gap-1"
                      title="Sign in to view historical snapshots"
                    >
                      🔒 {fmtDate(d)}
                    </Link>
                  )
                }

                return (
                  <Link
                    key={d}
                    href={isLatest ? "/tools/etb-tracker" : `/tools/etb-tracker?date=${d}`}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      isSelected
                        ? "bg-slate-600 text-white"
                        : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                    }`}
                  >
                    {fmtDate(d)}
                  </Link>
                )
              })}
            </div>
          )}
        </div>

        {!user && (
          <div className="mb-6 bg-slate-900 border border-slate-700 rounded-xl px-5 py-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-slate-200 text-sm font-medium">See how much premium you are paying</p>
              <p className="text-slate-500 text-xs mt-0.5">Sign in free to unlock sealed premium %, weekly price movers and your ETB watchlist</p>
            </div>
            <a href="/auth/google" className="bg-white text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors whitespace-nowrap">Sign in free</a>
          </div>
        )}

        {user && user.role === "free" && (
          <div className="mb-6 bg-slate-900 border border-yellow-500/20 rounded-xl px-5 py-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-slate-200 text-sm font-medium">Unlock PSA grading analysis</p>
              <p className="text-slate-500 text-xs mt-0.5">See raw promo prices, PSA 10 values, grading premium ratios and full score breakdowns for £3/month</p>
            </div>
            <a href="/premium" className="bg-yellow-500 text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-yellow-400 transition-colors whitespace-nowrap">Upgrade</a>
          </div>
        )}

        <Disclaimer />

        {etbs.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">ETBs Tracked</p>
              <p className="text-white text-2xl font-bold">{etbs.length}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">Avg Sealed Premium</p>
              <p className="text-white text-2xl font-bold">{(() => { const w = etbs.filter((e: any) => e.sealed_premium_pct != null); if (!w.length) return "N/A"; return (w.reduce((s: number, e: any) => s + e.sealed_premium_pct, 0) / w.length).toFixed(0) + "%" })()}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">MSRP</p>
              <p className="text-white text-2xl font-bold">£54.99</p>
            </div>
          </div>
        )}

        {isLoggedIn && isLatestDate && movers && movers.movers?.length > 0 && (
          <ETBMoversPanel movers={movers.movers} latest={movers.latest} previous={movers.previous} />
        )}

        {isLoggedIn && isLatestDate && movers && !movers.movers?.length && (
          <ETBMoversPanel movers={[]} latest={movers.latest} previous={movers.previous} />
        )}

        {!isLoggedIn && (
          <div className="mb-6 flex items-center gap-3 px-4 py-3 bg-slate-900/50 border border-slate-800 rounded-xl">
            <span className="text-slate-400 text-sm">Weekly price movers available with a free account</span>
            <a href="/auth/google" className="text-blue-400 text-sm font-medium hover:text-blue-300 whitespace-nowrap ml-auto">Sign in free →</a>
          </div>
        )}

        <div className="mt-4">
          {etbs.length > 0 ? (
            <ETBTable etbs={etbs} user={user} />
          ) : (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-12 text-center">
              <p className="text-slate-400">No ETB data available yet.</p>
            </div>
          )}
        </div>

        <p className="text-slate-600 text-xs mt-8">Sealed Premium = (Current price minus MSRP £54.99) divided by MSRP x 100. PSA Premium Ratio = PSA 10 promo price divided by Raw promo price. Prices sourced from eBay UK sold listings and Dawnglare. Updated weekly.</p>
      </div>
    </main>
    </>
  )
}
