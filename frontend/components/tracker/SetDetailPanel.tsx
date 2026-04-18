"use client"

import { useEffect } from "react"
import { formatGBP, formatPct, formatRatio, boxPctColor, scoreColor, recColor, generateReasoning } from "@/lib/format"
import { PriceTrend } from "@/components/tracker/PriceTrend"

interface Set {
  name: string
  era: string
  date_released: string
  print_status: string
  bb_price_gbp: number | null
  set_value_gbp: number | null
  top3_chase: string | null
  box_pct: number | null
  chase_pct: number | null
  recommendation: string | null
  scarcity: number | null
  liquidity: number | null
  mascot_power: number | null
  set_depth: number | null
  decision_score: number | null
}

interface User {
  authenticated: boolean
  email?: string
  role?: string
}


export function SetDetailPanel({ set, onClose, user }: { set: Set; onClose: () => void; user: User | null }) {
  const isLoggedIn = !!user
  const isPremium = user?.role === "premium" || user?.role === "admin"

  useEffect(() => {
    if (isLoggedIn && !isPremium) {
      const sid = sessionStorage.getItem("sid") || Math.random().toString(36).slice(2)
      sessionStorage.setItem("sid", sid)
      fetch("/api/internal?path=/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "upgrade_prompt_seen", page: "tracker", session_id: sid })
      })
    }
  }, [set.name])
  const reasoning = generateReasoning(set)

  const scores = [
    { label: "Scarcity",     value: set.scarcity,     max: 5 },
    { label: "Liquidity",    value: set.liquidity,     max: 5 },
    { label: "Mascot Power", value: set.mascot_power,  max: 5 },
    { label: "Set Depth",    value: set.set_depth,     max: 5 },
  ]

  // Parse top3_chase — only show if it looks like card names not a number
  const chaseIsNumeric = set.top3_chase ? !isNaN(Number(set.top3_chase)) : true
  const chaseCards = (!chaseIsNumeric && set.top3_chase) ? set.top3_chase.split(", ") : []

  return (
    <div
      className="fixed inset-0 bg-black/70 z-50 flex items-end md:items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-white">{set.name}</h2>
            <p className="text-slate-400 text-sm mt-1">
              {set.era} · {set.date_released}
              {set.print_status && (
                <span className="ml-2 text-slate-500">· {set.print_status}</span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 text-xl leading-none ml-4"
          >
            ✕
          </button>
        </div>

        {/* Key metrics — visible to all */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <Metric label="BB Price"  value={formatGBP(set.bb_price_gbp)} />
          <Metric label="Set Value" value={formatGBP(set.set_value_gbp)} />
          <Metric
            label="Box %"
            value={formatPct(set.box_pct)}
            colorClass={boxPctColor(set.box_pct)}
          />
        </div>

        {/* Chase % — visible to all */}
        <div className="bg-slate-800 rounded-xl p-4 mb-6">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Chase %</p>
          <p className="text-slate-200 text-sm">{formatRatio(set.chase_pct)}</p>
        </div>

        {/* Top 3 chase cards */}
        {chaseCards.length > 0 && (
          <div className="mb-6">
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">Top 3 chase cards</p>
            <div className="flex flex-wrap gap-2">
              {chaseCards.map((card, i) => (
                <span key={i} className="bg-slate-800 text-slate-300 text-xs px-3 py-1 rounded-full">
                  {card}
                </span>
              ))}
            </div>
            {/* Card prices — free with login */}
            {!isLoggedIn && (
              <p className="text-slate-500 text-xs mt-3">
                <a href="/auth/google" className="text-blue-400 hover:text-blue-300">Sign in free</a> to see individual card prices
              </p>
            )}
            {isLoggedIn && (
              <p className="text-slate-500 text-xs mt-2">
                Chase card % (top 3 ÷ set value): {formatRatio(set.chase_pct)}
              </p>
            )}
          </div>
        )}

        {/* Price trend — logged in only */}
        {isLoggedIn && (
          <div className="bg-slate-800 rounded-xl p-4 mb-6">
            <PriceTrend
              setName={set.name}
              
              
            />
          </div>
        )}

        {/* Recommendation, reasoning, score — premium only */}
        {isPremium ? (
          <>
            {set.recommendation && (
              <div className={`rounded-xl p-4 mb-4 text-center font-semibold text-lg ${recColor(set.recommendation)}`}>
                {set.recommendation}
              </div>
            )}

            {reasoning.length > 0 && set.recommendation && (
              <div className="bg-slate-800 rounded-xl p-4 mb-6">
                <p className="text-slate-400 text-xs uppercase tracking-wider mb-3">Why this rating</p>
                <ul className="space-y-2">
                  {reasoning.map((r, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-300">
                      <span className="text-slate-500 mt-0.5 shrink-0">•</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-slate-600 text-xs mt-3">
                  Note: AI decision scores are indicative and under review
                </p>
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-slate-400 text-xs uppercase tracking-wider">Score breakdown</p>
                <span className={`text-sm font-bold px-3 py-1 rounded-lg ${scoreColor(set.decision_score)}`}>
                  {set.decision_score ?? "—"} / 20
                </span>
              </div>
              <div className="space-y-3">
                {scores.map(({ label, value, max }) => (
                  <div key={label}>
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>{label}</span>
                      <span>{value ?? "—"} / {max}</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-slate-500 rounded-full transition-all"
                        style={{ width: value ? `${(value / max) * 100}%` : "0%" }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="border border-yellow-500/20 rounded-xl p-5 text-center">
            <p className="text-2xl mb-2">⭐</p>
            <p className="text-slate-200 font-medium text-sm mb-1">Recommendations and score breakdown are Premium features</p>
            <p className="text-slate-500 text-xs mb-4">
              Unlock buy/sell recommendations, AI reasoning, and full score breakdowns with a Premium account.
            </p>
            <a
              href="/premium"
              onClick={() => { const sid = sessionStorage.getItem("sid") || ""; fetch("/api/internal?path=/api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "upgrade_clicked", page: "tracker", session_id: sid }) }) }}
              className="inline-block bg-yellow-500 text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-yellow-400 transition-colors"
            >
              Upgrade to Premium — £3/month
            </a>
          </div>
        )}
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  colorClass,
}: {
  label: string
  value: string
  colorClass?: string
}) {
  return (
    <div className={`rounded-xl p-3 text-center ${colorClass ?? "bg-slate-800"}`}>
      <p className="text-xs mb-1 opacity-70">{label}</p>
      <p className="font-semibold text-sm">{value}</p>
    </div>
  )
}
