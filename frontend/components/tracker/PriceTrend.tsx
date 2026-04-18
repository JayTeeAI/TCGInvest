"use client"

import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface HistoryPoint {
  run_date: string
  bb_price_gbp: number | null
  box_pct: number | null
  decision_score: number | null
}

interface Props {
  setName: string
}

export function PriceTrend({ setName }: Props) {
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/internal?path=/api/sets/${encodeURIComponent(setName)}/history`)
      .then(r => r.json())
      .then(data => {
        setHistory(data.history || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [setName])

  const fmt = (d: string) => {
    const [y, m] = d.split("-")
    const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return `${months[parseInt(m)]} '${y.slice(2)}`
  }

  const chartData = history
    .filter(h => h.bb_price_gbp != null)
    .map(h => ({
      month:     fmt(h.run_date),
      price:     h.bb_price_gbp,
      boxPct:    h.box_pct != null ? Math.round(h.box_pct * 1000) / 10 : null,
      score:     h.decision_score,
    }))

  if (loading) {
    return <div className="h-32 flex items-center justify-center text-slate-500 text-sm">Loading...</div>
  }

  if (chartData.length < 2) {
    return <div className="h-32 flex items-center justify-center text-slate-500 text-sm">Not enough history yet</div>
  }

  const first = chartData[0].price ?? 0
  const last  = chartData[chartData.length - 1].price ?? 0
  const change = last - first
  const changePct = first > 0 ? ((change / first) * 100).toFixed(1) : null

  return (
    <div>
      {/* Summary line */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-slate-400 text-xs uppercase tracking-wider">Price trend (BB price GBP)</p>
        {changePct && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${change >= 0 ? "text-red-400" : "text-green-400"}`}>
            {change >= 0 ? "+" : ""}{changePct}% since {chartData[0].month}
          </span>
        )}
      </div>

      {/* BB Price chart */}
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v: any) => [`£${Number(v).toFixed(2)}`, "BB Price"]}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={{ fill: "#60a5fa", r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Box % chart */}
      <p className="text-slate-400 text-xs uppercase tracking-wider mt-4 mb-2">Box % trend</p>
      <ResponsiveContainer width="100%" height={60}>
        <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v: any) => [`${Number(v).toFixed(1)}%`, "Box %"]}
          />
          <Line
            type="monotone"
            dataKey="boxPct"
            stroke="#34d399"
            strokeWidth={2}
            dot={{ fill: "#34d399", r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Score row */}
      {chartData.some(d => d.score != null) && (
        <div className="flex gap-3 mt-4">
          {chartData.map(d => (
            <div key={d.month} className="flex-1 bg-slate-800 rounded-lg p-2 text-center">
              <p className="text-slate-500 text-xs">{d.month}</p>
              <p className="text-slate-200 text-sm font-semibold">{d.score ?? "—"}</p>
              <p className="text-slate-600 text-xs">score</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
