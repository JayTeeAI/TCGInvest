"use client"

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface HistoryPoint {
  snapshot_date: string
  ebay_avg_sold_gbp: number | null
  sealed_premium_pct: number | null
}

interface Props {
  history: HistoryPoint[]
  etbName: string
}

function fmt(d: string): string {
  const parts = d.slice(0, 7).split("-")
  const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
  return `${months[parseInt(parts[1])]} '${parts[0].slice(2)}`
}

export function ETBPageClient({ history, etbName }: Props) {
  const chartData = history
    .filter(h => h.ebay_avg_sold_gbp != null)
    .map(h => ({
      month: fmt(h.snapshot_date),
      price: h.ebay_avg_sold_gbp,
      premium: h.sealed_premium_pct != null ? Math.round(h.sealed_premium_pct) : null,
    }))

  if (chartData.length < 2) {
    return <div className="h-32 flex items-center justify-center text-slate-500 text-sm">Not enough history yet for {etbName}</div>
  }

  const first = chartData[0].price ?? 0
  const last  = chartData[chartData.length - 1].price ?? 0
  const change = last - first
  const changePct = first > 0 ? ((change / first) * 100).toFixed(1) : null

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-slate-400 text-xs uppercase tracking-wider">Sealed Price (GBP)</p>
        {changePct && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${change >= 0 ? "text-red-400" : "text-green-400"}`}>
            {change >= 0 ? "+" : ""}{changePct}% since {chartData[0].month}
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v: any) => [`£${Number(v).toFixed(2)}`, "Sealed Price"]}
          />
          <Line type="monotone" dataKey="price" stroke="#60a5fa" strokeWidth={2} dot={{ fill: "#60a5fa", r: 3 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>

      {chartData.some(d => d.premium != null) && (
        <>
          <p className="text-slate-400 text-xs uppercase tracking-wider mt-4 mb-2">Sealed Premium %</p>
          <ResponsiveContainer width="100%" height={80}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis hide domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(v: any) => [`${Number(v).toFixed(0)}%`, "Sealed Premium"]}
              />
              <Line type="monotone" dataKey="premium" stroke="#f59e0b" strokeWidth={2} dot={{ fill: "#f59e0b", r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
