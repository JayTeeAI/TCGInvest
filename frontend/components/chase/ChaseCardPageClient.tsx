"use client"

import SetAlertButton from '@/components/alerts/SetAlertButton'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"

interface HistoryPoint {
  snapshot_date: string
  raw_gbp: number | null
  psa10_gbp: number | null
}

interface CardDetail {
  id: number
  card_name: string
  set_name: string
  image_url: string | null
  pull_rate_per_box: number | null
  raw_gbp: number | null
  psa10_gbp: number | null
  grade_roi_gbp: number | null
  grade_signal: "worth_it" | "marginal" | "not_worth_it" | null
  snapshot_date: string | null
  rarity: string | null
  card_type: string | null
  card_stage: string | null
}

interface Props {
  card: CardDetail
  history: HistoryPoint[]
}

function fmt(v: number | null): string {
  if (v == null) return "—"
  return `£${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function GradeSignalBadge({ signal }: { signal: CardDetail["grade_signal"] }) {
  if (!signal) return null
  if (signal === "worth_it")
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-500/15 text-green-400 text-sm font-semibold border border-green-500/20">✓ Worth Grading</span>
  if (signal === "marginal")
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-yellow-500/15 text-yellow-400 text-sm font-semibold border border-yellow-500/20">~ Marginal</span>
  return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-red-500/15 text-red-400 text-sm font-semibold border border-red-500/20">✗ Not Worth Grading</span>
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-white/5 last:border-0">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className="text-white text-sm font-medium">{value}</span>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm shadow-xl">
      <p className="text-gray-400 mb-1.5">{new Date(label).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-mono font-medium">
          {p.name}: £{Number(p.value).toFixed(2)}
        </p>
      ))}
    </div>
  )
}

export function ChaseCardPageClient({ card, history }: Props) {
  // Reverse history so chart is chronological (oldest → newest)
  const chartData = [...history].reverse().map(h => ({
    date: h.snapshot_date,
    raw_gbp: h.raw_gbp,
    psa10_gbp: h.psa10_gbp,
  }))

  const roiColour = card.grade_roi_gbp == null
    ? "text-gray-400"
    : card.grade_roi_gbp >= 0 ? "text-green-400" : "text-red-400"

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="text-xs text-gray-500 mb-6">
        <a href="/tools/chase-cards" className="hover:text-gray-300 transition-colors">Chase Cards</a>
        <span className="mx-2">/</span>
        <span className="text-gray-300">{card.card_name}</span>
      </nav>

      {/* Hero section */}
      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-8 mb-10">
        {/* Card image */}
        <div className="flex justify-center lg:justify-start">
          {card.image_url ? (
            <img
              src={card.image_url}
              alt={card.card_name}
              className="w-56 lg:w-full max-w-[280px] rounded-2xl shadow-2xl object-cover"
              loading="eager"
            />
          ) : (
            <div className="w-56 lg:w-full max-w-[280px] aspect-[2/3] rounded-2xl bg-slate-800 flex items-center justify-center text-gray-600 text-sm">
              No image available
            </div>
          )}
        </div>

        {/* Metadata panel */}
        <div className="flex flex-col justify-between gap-6">
          <div>
            <p className="text-yellow-400 text-sm font-medium mb-1">{card.set_name}</p>
            <h1 className="text-2xl lg:text-3xl font-bold text-white leading-tight mb-4">{card.card_name}</h1>
            <GradeSignalBadge signal={card.grade_signal} />
          </div>

          {/* Card metadata */}
          <div className="bg-white/4 border border-white/8 rounded-2xl px-5 py-1 divide-y divide-white/5">
            <MetaRow label="Set" value={card.set_name} />
            {card.rarity && <MetaRow label="Rarity" value={card.rarity} />}
            {card.card_type && <MetaRow label="Type" value={card.card_type} />}
            {card.card_stage && <MetaRow label="Stage" value={card.card_stage} />}
            {card.pull_rate_per_box != null && (
              <MetaRow label="Pull Rate per Box" value={`1 in ${card.pull_rate_per_box}`} />
            )}
          </div>

          {/* Price section */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white/4 border border-white/8 rounded-2xl p-4 text-center">
              <p className="text-gray-400 text-xs mb-1.5">Raw (Ungraded)</p>
              <p className="text-white text-xl font-bold font-mono">{fmt(card.raw_gbp)}</p>
            </div>
            <div className="bg-white/4 border border-white/8 rounded-2xl p-4 text-center">
              <p className="text-gray-400 text-xs mb-1.5">PSA 10</p>
              <p className="text-white text-xl font-bold font-mono">{fmt(card.psa10_gbp)}</p>
            </div>
            <div className="bg-white/4 border border-white/8 rounded-2xl p-4 text-center">
              <p className="text-gray-400 text-xs mb-1.5">Grade ROI</p>
              <p className={`text-xl font-bold font-mono ${roiColour}`}>
                {card.grade_roi_gbp != null
                  ? `${card.grade_roi_gbp >= 0 ? "+" : ""}${fmt(card.grade_roi_gbp)}`
                  : "—"}
              </p>
            </div>
          </div>
          <p className="text-gray-600 text-xs -mt-3">Grade ROI = PSA 10 − Raw − £20 grading fee</p>
          {card.raw_gbp && (
            <div className="mt-4">
              <SetAlertButton
                productType="chase_card"
                productId={card.id}
                productName={card.card_name}
                currentPrice={card.raw_gbp}
              />
            </div>
          )}
        </div>
      </div>

      {/* Price history chart */}
      {chartData.length >= 2 && (
        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 mb-8">
          <h2 className="text-white font-semibold text-lg mb-6">Price History</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                tickFormatter={d => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                tickLine={false}
                axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
              />
              <YAxis
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                tickFormatter={v => `£${v}`}
                tickLine={false}
                axisLine={false}
                width={55}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: "13px", color: "#9ca3af", paddingTop: "12px" }}
              />
              <Line
                type="monotone"
                dataKey="raw_gbp"
                name="Raw"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="psa10_gbp"
                name="PSA 10"
                stroke="#facc15"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {chartData.length < 2 && (
        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 mb-8 text-center text-gray-500 text-sm">
          Collecting data — check back after the next weekly update for a full trend.
        </div>
      )}

      {/* Snapshot date footer */}
      {card.snapshot_date && (
        <p className="text-gray-600 text-xs text-center">
          Prices last updated {new Date(card.snapshot_date).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} · Source: PriceCharting
        </p>
      )}
    </div>
  )
}
