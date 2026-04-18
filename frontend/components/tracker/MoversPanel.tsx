"use client"

import { formatGBP } from "@/lib/format"

interface Mover {
  name: string
  era: string
  curr_bb: number | null
  prev_bb: number | null
  bb_change: number | null
  bb_change_pct: number | null
  curr_box_pct: number | null
  prev_box_pct: number | null
  box_pct_change: number | null
  curr_score: number | null
  prev_score: number | null
  score_change: number | null
  curr_rec: string | null
}

interface Props {
  movers: Mover[]
  latest: string
  previous: string
}

export function MoversPanel({ movers, latest, previous }: Props) {
  const withBBChange = movers.filter(m => m.bb_change !== null)

  const biggestDrops = [...withBBChange]
    .sort((a, b) => (a.bb_change ?? 0) - (b.bb_change ?? 0))
    .slice(0, 4)

  const biggestRises = [...withBBChange]
    .sort((a, b) => (b.bb_change ?? 0) - (a.bb_change ?? 0))
    .slice(0, 4)

  const bestBoxPct = [...movers]
    .filter(m => m.box_pct_change !== null)
    .sort((a, b) => (a.box_pct_change ?? 0) - (b.box_pct_change ?? 0))
    .slice(0, 4)

  const fmt = (d: string) => {
    const [y, m] = d.split("-")
    const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return `${months[parseInt(m)]} ${y.slice(2)}`
  }

  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-slate-300 font-semibold">Month-on-month changes</h2>
        <span className="text-slate-500 text-sm">{fmt(previous)} → {fmt(latest)}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* BB Price drops */}
        <MoverCard
          title="Biggest price drops"
          subtitle="BB price fell most"
          items={biggestDrops}
          metric={(m) => ({
            primary: m.bb_change != null ? `${m.bb_change > 0 ? "+" : ""}${formatGBP(m.bb_change)}` : "—",
            secondary: m.bb_change_pct != null ? `${m.bb_change_pct > 0 ? "+" : ""}${m.bb_change_pct}%` : "",
            positive: (m.bb_change ?? 0) < 0,
            isNegativeGood: true,
          })}
        />

        {/* BB Price rises */}
        <MoverCard
          title="Biggest price rises"
          subtitle="BB price increased most"
          items={biggestRises}
          metric={(m) => ({
            primary: m.bb_change != null ? `${m.bb_change > 0 ? "+" : ""}${formatGBP(m.bb_change)}` : "—",
            secondary: m.bb_change_pct != null ? `${m.bb_change_pct > 0 ? "+" : ""}${m.bb_change_pct}%` : "",
            positive: (m.bb_change ?? 0) > 0,
            isNegativeGood: false,
          })}
        />

        {/* Box % improved (lower = better) */}
        <MoverCard
          title="Box % improved"
          subtitle="Getting cheaper vs set value"
          items={bestBoxPct}
          metric={(m) => {
            const change = m.box_pct_change
            const pct = change != null ? (change * 100).toFixed(1) : null
            return {
              primary: pct != null ? `${change! > 0 ? "+" : ""}${pct}%` : "—",
              secondary: m.curr_box_pct != null ? `Now ${(m.curr_box_pct * 100).toFixed(1)}%` : "",
              positive: (change ?? 0) < 0,
              isNegativeGood: true,
            }
          }}
        />
      </div>
    </div>
  )
}

interface MoverCardProps {
  title: string
  subtitle: string
  items: Mover[]
  metric: (m: Mover) => {
    primary: string
    secondary: string
    positive: boolean
    isNegativeGood: boolean
  }
}

function MoverCard({ title, subtitle, items, metric }: MoverCardProps) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
      <p className="text-white text-sm font-semibold mb-1">{title}</p>
      <p className="text-slate-500 text-xs mb-4">{subtitle}</p>
      <div className="space-y-3">
        {items.map(m => {
          const { primary, secondary, positive } = metric(m)
          return (
            <div key={m.name} className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-slate-200 text-sm truncate">{m.name}</p>
                <p className="text-slate-500 text-xs">{m.era}</p>
              </div>
              <div className="text-right shrink-0">
                <p className={`text-sm font-semibold ${positive ? "text-green-400" : "text-red-400"}`}>
                  {primary}
                </p>
                <p className="text-slate-500 text-xs">{secondary}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
