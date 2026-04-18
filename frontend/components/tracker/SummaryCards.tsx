"use client"

import { useState } from "react"

interface Stats {
  buy_count: number
  strong_buy_count: number
  avg_box_pct: number
  best_box_pct: number
}

interface Set {
  name: string
  recommendation: string | null
  box_pct: number | null
  bb_price_gbp: number | null
  set_value_gbp: number | null
}

interface User {
  authenticated: boolean
  role?: string
}

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ""

export function SummaryCards({ stats, user }: { stats: Stats; user: User | null }) {
  const isLoggedIn = !!user
  const isPremium = user?.role === "premium" || user?.role === "admin"
  const [popup, setPopup] = useState<string | null>(null)
  const [sets, setSets] = useState<Set[]>([])
  const [loading, setLoading] = useState(false)
  const [upgradeNudge, setUpgradeNudge] = useState(false)

  async function handleClick(card: string) {
    if (!isPremium) {
      setUpgradeNudge(true)
      return
    }
    setLoading(true)
    setPopup(card)
    try {
      const res = await fetch("/api/sets", {
        headers: { "X-API-Key": API_KEY },
        cache: "no-store",
      })
      const data = await res.json()
      setSets(data.sets || [])
    } catch {}
    setLoading(false)
  }

  function closePopup() { setPopup(null); setSets([]) }

  const buySignals = sets.filter(s => ["Strong Buy", "Buy", "Accumulate"].includes(s.recommendation || ""))
  const strongBuys = sets.filter(s => s.recommendation === "Strong Buy")
  const bestSet = sets.length > 0 ? sets.reduce((a, b) => (a.box_pct ?? 999) < (b.box_pct ?? 999) ? a : b) : null

  const fmt = (n: number | null) => n != null ? `£${n.toFixed(2)}` : "—"
  const fmtPct = (n: number | null) => n != null ? `${(n * 100).toFixed(1)}%` : "—"

  return (
    <>
      {/* Upgrade nudge */}
      {upgradeNudge && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setUpgradeNudge(false)}>
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-sm w-full text-center" onClick={e => e.stopPropagation()}>
            <p className="text-2xl mb-3">⭐</p>
            <h3 className="text-white font-bold text-lg mb-2">Premium feature</h3>
            <p className="text-slate-400 text-sm mb-5">Upgrade to Premium to drill into buy signals, strong buys, and best value sets.</p>
            <a href="/premium" className="block w-full bg-yellow-500 text-slate-900 font-medium py-2.5 rounded-lg hover:bg-yellow-400 transition-colors mb-3">
              Upgrade to Premium — £3/month
            </a>
            <button onClick={() => setUpgradeNudge(false)} className="text-slate-500 text-sm hover:text-slate-300">Maybe later</button>
          </div>
        </div>
      )}

      {/* Drill-down popup */}
      {popup && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={closePopup}>
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-bold text-lg">
                {popup === "buy" && `Buy Signals (${buySignals.length})`}
                {popup === "strong" && `Strong Buys (${strongBuys.length})`}
                {popup === "best" && "Best Value Box"}
              </h3>
              <button onClick={closePopup} className="text-slate-500 hover:text-slate-300 text-xl">✕</button>
            </div>
            {loading ? (
              <p className="text-slate-400 text-sm text-center py-8">Loading...</p>
            ) : (
              <>
                {(popup === "buy" || popup === "strong") && (
                  <div className="space-y-2">
                    {(popup === "buy" ? buySignals : strongBuys).map(s => (
                      <div key={s.name} className="flex items-center justify-between bg-slate-800 rounded-xl px-4 py-3">
                        <div>
                          <p className="text-white text-sm font-medium">{s.name}</p>
                          <p className="text-slate-400 text-xs mt-0.5">Box %: {fmtPct(s.box_pct)}</p>
                        </div>
                        <span className="text-xs font-medium px-2 py-1 rounded bg-green-900 text-green-300">{s.recommendation}</span>
                      </div>
                    ))}
                  </div>
                )}
                {popup === "best" && bestSet && (
                  <div className="bg-slate-800 rounded-xl p-5">
                    <p className="text-white font-bold text-xl mb-4">{bestSet.name}</p>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-slate-900 rounded-xl p-3 text-center">
                        <p className="text-slate-400 text-xs mb-1">Box %</p>
                        <p className="text-green-400 font-bold">{fmtPct(bestSet.box_pct)}</p>
                      </div>
                      <div className="bg-slate-900 rounded-xl p-3 text-center">
                        <p className="text-slate-400 text-xs mb-1">BB Price</p>
                        <p className="text-white font-medium text-sm">{fmt(bestSet.bb_price_gbp)}</p>
                      </div>
                      <div className="bg-slate-900 rounded-xl p-3 text-center">
                        <p className="text-slate-400 text-xs mb-1">Set Value</p>
                        <p className="text-white font-medium text-sm">{fmt(bestSet.set_value_gbp)}</p>
                      </div>
                    </div>
                    {bestSet.recommendation && (
                      <p className="text-center mt-4 text-green-300 text-sm font-medium">{bestSet.recommendation}</p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Cards — only show if logged in */}
      {isLoggedIn && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          <Card label="BUY SIGNALS" value={String(stats.buy_count)} color="text-green-400" onClick={() => handleClick("buy")} clickable={true} />
          <Card label="STRONG BUYS" value={String(stats.strong_buy_count)} color="text-green-400" onClick={() => handleClick("strong")} clickable={true} />
          <Card label="AVG BOX %" value={`${(stats.avg_box_pct * 100).toFixed(1)}%`} color="text-white" clickable={false} />
          <Card label="BEST BOX %" value={`${(stats.best_box_pct * 100).toFixed(1)}%`} color="text-green-400" onClick={() => handleClick("best")} clickable={true} />
        </div>
      )}
    </>
  )
}

function Card({ label, value, color, onClick, clickable }: { label: string; value: string; color: string; onClick?: () => void; clickable: boolean }) {
  return (
    <div
      className={`bg-slate-900 border border-slate-800 rounded-xl p-5 ${clickable ? "cursor-pointer hover:border-slate-600 transition-colors" : ""}`}
      onClick={clickable ? onClick : undefined}
    >
      <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {clickable && <p className="text-slate-600 text-xs mt-2">click to explore →</p>}
    </div>
  )
}
