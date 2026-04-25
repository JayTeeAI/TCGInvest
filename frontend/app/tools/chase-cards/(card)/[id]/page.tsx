import { getChaseCard, getChaseCardHistory } from "@/lib/api"
import { getUser } from "@/lib/auth"
import { ChaseCardPageClient } from "@/components/chase/ChaseCardPageClient"
import { notFound } from "next/navigation"
import type { Metadata } from "next"

export const revalidate = 3600

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params
  const cardId = parseInt(id, 10)
  if (isNaN(cardId)) return { title: "Not Found" }

  const title = `Chase Card #${cardId} — Chase Card Tracker | TCGInvest`
  const description = `Track raw and PSA 10 prices, grading ROI, pull rate, and price history for this Pokémon TCG chase card. Updated weekly.`
  const canonical = `https://tcginvest.uk/tools/chase-cards/${cardId}`

  return {
    title,
    description,
    robots: { index: false, follow: true },
    alternates: { canonical },
    openGraph: {
      title,
      description,
      url: canonical,
      images: [{ url: "https://tcginvest.uk/og-chase-cards.png", width: 1200, height: 630 }],
    },
  }
}

export default async function ChaseCardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const cardId = parseInt(id, 10)
  if (isNaN(cardId)) notFound()

  const [cardResult, historyResult, userData] = await Promise.allSettled([
    getChaseCard(cardId),
    getChaseCardHistory(cardId),
    getUser(),
  ])

  const card = cardResult.status === "fulfilled" ? cardResult.value : null
  const historyData = historyResult.status === "fulfilled" ? historyResult.value : null
  const user = userData.status === "fulfilled" && userData.value?.authenticated ? userData.value : null
  const isPremium = user?.role === "premium" || user?.role === "admin"

  if (!card) notFound()

  const history = historyData?.history ?? []
  const cardName = card.card_name ?? "Chase Card"
  const setName = card.set_name ?? "Pokémon TCG"

  // ── Teaser for free / logged-out ──────────────────────────────────────────
  if (!isPremium) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-16 text-center">
        <nav className="text-xs text-gray-500 mb-8 text-left">
          <a href="/tools/chase-cards" className="hover:text-gray-300 transition-colors">Chase Cards</a>
          <span className="mx-2">/</span>
          <span className="text-gray-300">{cardName}</span>
        </nav>

        <div className="relative w-44 mx-auto mb-8">
          <div className="aspect-[2/3] rounded-2xl bg-gradient-to-br from-slate-700 to-slate-800 border border-white/10 flex items-center justify-center">
            <span className="text-5xl">✨</span>
          </div>
          <div className="absolute inset-0 backdrop-blur-sm rounded-2xl" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-3xl">🔒</span>
          </div>
        </div>

        <h1 className="text-2xl font-bold text-white mb-2">{cardName}</h1>
        <p className="text-gray-400 text-sm mb-8">{setName}</p>

        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 mb-8 max-w-md mx-auto text-left space-y-2.5">
          <p className="text-gray-300 text-sm font-semibold mb-3">This page includes:</p>
          {[
            "📈 Raw (ungraded) price in GBP",
            "🏆 PSA 10 graded price in GBP",
            "💰 Grading ROI — net profit after £20 PSA fee",
            "🟢 Grade Signal — Worth It / Marginal / Not Worth It",
            "📊 12-week price history chart",
            "📦 Pull rate per booster box",
          ].map(item => (
            <div key={item} className="text-gray-400 text-sm">{item}</div>
          ))}
        </div>

        <a
          href="/premium"
          className="inline-flex items-center gap-2 bg-yellow-400 hover:bg-yellow-300 text-black font-bold px-8 py-3.5 rounded-xl text-sm transition-colors"
        >
          Unlock with Premium — £3/month →
        </a>

        {!user && (
          <p className="mt-4 text-gray-600 text-xs">
            Already premium?{" "}
            <a href="/auth/login" className="text-gray-400 underline hover:text-white">Sign in</a>
          </p>
        )}
      </main>
    )
  }

  // ── Full premium page ─────────────────────────────────────────────────────
  return <ChaseCardPageClient card={card} history={history} />
}
