"use client"

import type { User } from "@/lib/auth"
import { useState, useEffect } from "react"

interface ChaseCard {
  id: number
  card_name: string
  card_number: string | null
  rarity: string | null
  image_url: string | null
  raw_gbp: number | null
  psa10_gbp: number | null
  raw_delta_pct: number | null
  psa10_delta_pct: number | null
  grade_mult: number | null
  grade_roi_gbp: number | null
  grade_roi_pct: number | null
  grade_signal: "worth_it" | "marginal" | "not_worth_it" | null
  pull_rate: number | null
  pull_ev: number | null
  snapshot_date: string | null
  rank: number
  pc_path: string | null
}

interface SetData {
  set_id: number
  set_name: string
  era: string
  logo_url: string | null
  cards: ChaseCard[]
  top3_pull_ev: number | null
}

interface Props {
  sets: SetData[]
  gradingFee: number
  user: User | null
}

function fmt(v: number | null, prefix = "£"): string {
  if (v == null) return "—"
  return `${prefix}${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function DeltaBadge({ pct }: { pct: number | null }) {
  if (pct == null) return null
  const pos = pct >= 0
  return (
    <span className={`text-xs font-medium ml-1 ${pos ? "text-green-400" : "text-red-400"}`}>
      {pos ? "▲" : "▼"}{Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function GradeSignal({ signal }: { signal: ChaseCard["grade_signal"] }) {
  if (!signal) return null
  if (signal === "worth_it")    return <span className="text-green-400 text-xs font-semibold">✓ Worth it</span>
  if (signal === "marginal")    return <span className="text-yellow-400 text-xs font-semibold">~ Marginal</span>
  return <span className="text-red-400 text-xs font-semibold">✗ Skip</span>
}

function StarButton({
  cardId,
  isStarred,
  onToggle,
}: {
  cardId: number
  isStarred: boolean
  onToggle: (id: number, starred: boolean) => void
}) {
  return (
    <button
      onClick={() => onToggle(cardId, isStarred)}
      aria-label={isStarred ? "Remove from watchlist" : "Add to watchlist"}
      className="p-1 rounded hover:bg-white/10 transition-colors"
      title={isStarred ? "Remove from watchlist" : "Add to watchlist"}
    >
      <span className={`text-base leading-none ${isStarred ? "text-yellow-400" : "text-gray-600 hover:text-gray-400"}`}>
        {isStarred ? "★" : "☆"}
      </span>
    </button>
  )
}

function CardTile({
  card,
  gradingFee,
  isStarred,
  canStar,
  onToggleStar,
  linkHref,
  onClick,
}: {
  card: ChaseCard
  gradingFee: number
  isStarred: boolean
  canStar: boolean
  onToggleStar: (id: number, starred: boolean) => void
  linkHref: string
  onClick: () => void
}) {
  return (
    <a href={linkHref} className="bg-white/[0.04] rounded-xl border border-white/10 overflow-hidden flex flex-row hover:border-white/20 hover:bg-white/[0.07] transition-colors no-underline block">
      <div className="shrink-0 w-28 sm:w-32 bg-black/30 flex items-center justify-center">
        {card.image_url ? (
          <img src={card.image_url} alt={card.card_name} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full min-h-[8rem] flex items-center justify-center text-gray-700 text-xs">No image</div>
        )}
      </div>
      <div className="flex-1 p-3 flex flex-col justify-between min-w-0">
        <div className="mb-2">
          <div className="flex items-start justify-between gap-1">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-gray-500 text-xs">#{card.rank}</span>
              </div>
              <div className="text-white font-semibold text-sm leading-snug">{card.card_name}</div>
              {card.card_number && <div className="text-gray-500 text-xs mt-0.5">{card.card_number}</div>}
            </div>
            {canStar && (
              <div className="shrink-0 -mt-0.5" onClick={e => e.stopPropagation()}>
                <StarButton cardId={card.id} isStarred={isStarred} onToggle={onToggleStar} />
              </div>
            )}
          </div>
        </div>
        {card.raw_gbp == null ? (
          <div className="mt-2 text-xs text-gray-500 italic">Price unavailable</div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div>
                <div className="text-gray-400 text-xs">Raw</div>
                <div className="text-white font-mono font-medium">{fmt(card.raw_gbp)}<DeltaBadge pct={card.raw_delta_pct} /></div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">PSA 10</div>
                <div className="text-white font-mono font-medium">{fmt(card.psa10_gbp)}<DeltaBadge pct={card.psa10_delta_pct} /></div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Grade ×</div>
                <div className="text-gray-200 font-mono">{card.grade_mult != null ? `${card.grade_mult}×` : "—"}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Grade ROI</div>
                <div className={`font-mono ${card.grade_roi_gbp == null ? "text-gray-500" : card.grade_roi_gbp > 0 ? "text-green-400" : "text-red-400"}`}>
                  {card.grade_roi_gbp != null ? `${card.grade_roi_gbp >= 0 ? "+" : ""}${fmt(card.grade_roi_gbp)}` : "—"}
                </div>
                <GradeSignal signal={card.grade_signal} />
              </div>
            </div>
            {card.pull_ev != null && (
              <div className="mt-2 pt-2 border-t border-white/10 flex items-center justify-between text-xs text-gray-500">
                <span>Pull EV/box</span>
                <span className="text-gray-300 font-mono">{fmt(card.pull_ev)}</span>
              </div>
            )}
          </>
        )}
      </div>
    </a>
  )
}

function SetBlock({
  setData,
  gradingFee,
  visibleCards,
  starredIds,
  canStar,
  isPremium,
  onToggleStar,
  onCardClick,
}: {
  setData: SetData
  gradingFee: number
  visibleCards: ChaseCard[]
  starredIds: Set<number>
  canStar: boolean
  isPremium: boolean
  onToggleStar: (id: number, starred: boolean) => void
  onCardClick: (card: ChaseCard, setName: string) => void
}) {
  return (
    <section className="mb-10">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          {setData.logo_url && (
            <img src={setData.logo_url} alt={`${setData.set_name} logo`} className="h-8 w-auto object-contain" loading="lazy" />
          )}
          <div>
            <h2 className="text-white font-bold text-lg leading-tight">{setData.set_name}</h2>
            <span className="text-gray-500 text-xs uppercase tracking-wide">{setData.era}</span>
          </div>
        </div>
        {setData.top3_pull_ev != null && (
          <div className="text-right shrink-0">
            <div className="text-gray-500 text-xs">Pull EV/box</div>
            <div className="text-gray-200 font-mono text-sm font-semibold">{fmt(setData.top3_pull_ev)}</div>
          </div>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {visibleCards.map(card => (
          <CardTile
            key={card.id}
            card={card}
            gradingFee={gradingFee}
            isStarred={starredIds.has(card.id)}
            canStar={canStar}
            linkHref={isPremium ? `/tools/chase-cards/${card.id}` : "/premium"}
            onToggleStar={onToggleStar}
            onClick={() => onCardClick(card, setData.set_name)}
          />
        ))}
      </div>
      <p className="text-gray-700 text-xs mt-2 px-0.5">Grade ROI assumes £{gradingFee} PSA grading fee.</p>
    </section>
  )
}

export function ChaseCardTable({ sets, gradingFee, user }: Props) {
  const [search, setSearch] = useState("")
  const [sortBy, setSortBy] = useState<"default" | "top_raw" | "top_psa10">("default")
  const [starredIds, setStarredIds] = useState<Set<number>>(new Set())
  const [starError, setStarError] = useState<string | null>(null)
  const [selectedCard, setSelectedCard] = useState<{ card: ChaseCard; setName: string } | null>(null)

  const canStar = !!user
  const isPremium = user?.role === "premium" || user?.role === "admin"

  const latestSnapshot = sets
    .flatMap(s => s.cards)
    .map(c => c.snapshot_date)
    .filter(Boolean)
    .sort()
    .at(-1)

  const formattedDate = latestSnapshot
    ? new Date(latestSnapshot).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
    : null

  useEffect(() => {
    if (!user) return
    fetch("/api/chase-watchlist", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.watchlist) setStarredIds(new Set(data.watchlist)) })
      .catch(() => {})
  }, [user])

  const handleToggleStar = async (cardId: number, currentlyStarred: boolean) => {
    if (!user) return
    setStarError(null)
    const optimistic = new Set(starredIds)
    if (currentlyStarred) { optimistic.delete(cardId) } else { optimistic.add(cardId) }
    setStarredIds(optimistic)
    const res = await fetch(`/api/chase-watchlist/${cardId}`, {
      method: currentlyStarred ? "DELETE" : "POST",
      credentials: "include",
    })
    if (!res.ok) {
      setStarredIds(starredIds)
      if (res.status === 403) {
        const data = await res.json().catch(() => ({}))
        setStarError(data.detail || "Watchlist limit reached. Upgrade to Premium for unlimited.")
      } else {
        setStarError("Failed to update watchlist. Please try again.")
      }
    }
  }

  if (!sets || sets.length === 0) {
    return <div className="text-gray-400 text-center py-16">No chase card data available yet.</div>
  }

  const lowerSearch = search.toLowerCase()
  type FilteredSet = { setData: SetData; visibleCards: ChaseCard[] }
  const filtered: FilteredSet[] = []

  for (const s of sets) {
    if (!search) {
      filtered.push({ setData: s, visibleCards: s.cards.slice(0, 3) })
      continue
    }
    if (s.set_name.toLowerCase().includes(lowerSearch)) {
      filtered.push({ setData: s, visibleCards: s.cards.slice(0, 3) })
    } else {
      const matchingCards = s.cards.filter(c => c.card_name.toLowerCase().includes(lowerSearch))
      if (matchingCards.length > 0) filtered.push({ setData: s, visibleCards: matchingCards })
    }
  }

  if (sortBy === "top_raw") {
    filtered.sort((a, b) =>
      Math.max(...b.visibleCards.map(c => c.raw_gbp ?? 0)) - Math.max(...a.visibleCards.map(c => c.raw_gbp ?? 0))
    )
  } else if (sortBy === "top_psa10") {
    filtered.sort((a, b) =>
      Math.max(...b.visibleCards.map(c => c.psa10_gbp ?? 0)) - Math.max(...a.visibleCards.map(c => c.psa10_gbp ?? 0))
    )
  }

  return (
    <div>
      {formattedDate && (
        <p className="text-gray-500 text-xs mb-6">
          Updated {formattedDate} · Prices from PriceCharting sold listings · Converted to GBP at live rate
        </p>
      )}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        <input
          type="text"
          placeholder="Search set or card…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-white/30"
        />
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as typeof sortBy)}
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-gray-300 text-sm focus:outline-none focus:border-white/30"
        >
          <option value="default">Sort: Default</option>
          <option value="top_raw">Sort: Highest Raw Price</option>
          <option value="top_psa10">Sort: Highest PSA 10</option>
        </select>
      </div>
      {!user && (
        <div className="mb-6 bg-yellow-400/10 border border-yellow-400/20 rounded-lg px-4 py-3 text-sm text-yellow-300">
          <a href="/auth/login" className="font-semibold underline">Sign in</a> to star cards and track them in your weekly digest.
        </div>
      )}
      {starError && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-300 flex items-center justify-between">
          <span>{starError}</span>
          <button onClick={() => setStarError(null)} className="ml-4 text-red-400 hover:text-red-200">✕</button>
        </div>
      )}
      {filtered.length === 0 ? (
        <div className="text-gray-400 text-center py-12">No cards match your search.</div>
      ) : (
        filtered.map(({ setData, visibleCards }) => (
          <SetBlock
            key={setData.set_id}
            setData={setData}
            gradingFee={gradingFee}
            visibleCards={visibleCards}
            starredIds={starredIds}
            canStar={canStar}
            isPremium={isPremium}
            onToggleStar={handleToggleStar}
            onCardClick={(card, setName) => setSelectedCard({ card, setName })}
          />
        ))
      )}
      {selectedCard && (
        <div
          className="fixed inset-0 bg-black/70 z-50 flex items-end md:items-center justify-center p-4"
          onClick={() => setSelectedCard(null)}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start gap-4 p-5">
              {selectedCard.card.image_url ? (
                <img
                  src={selectedCard.card.image_url}
                  alt={selectedCard.card.card_name}
                  className="w-28 rounded-lg object-cover shrink-0"
                />
              ) : (
                <div className="w-28 h-40 bg-slate-800 rounded-lg shrink-0 flex items-center justify-center text-slate-600 text-xs">No image</div>
              )}
              <div className="flex-1 min-w-0">
                <div className="text-slate-400 text-xs mb-0.5">{selectedCard.setName}</div>
                <div className="text-white font-bold text-base leading-snug mb-3">{selectedCard.card.card_name}</div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Raw</span>
                    <span className="text-white font-mono font-medium">{fmt(selectedCard.card.raw_gbp)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">PSA 10</span>
                    <span className="text-white font-mono font-medium">{fmt(selectedCard.card.psa10_gbp)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Grade ROI</span>
                    <span className={`font-mono font-medium ${selectedCard.card.grade_roi_gbp == null ? "text-slate-500" : selectedCard.card.grade_roi_gbp >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {selectedCard.card.grade_roi_gbp != null ? `${selectedCard.card.grade_roi_gbp >= 0 ? "+" : ""}${fmt(selectedCard.card.grade_roi_gbp)}` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-slate-400">Signal</span>
                    <GradeSignal signal={selectedCard.card.grade_signal} />
                  </div>
                </div>
              </div>
            </div>
            <div className="px-5 pb-5">
              <button
                onClick={() => setSelectedCard(null)}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
