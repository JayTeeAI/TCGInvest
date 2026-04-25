"use client"

import { useState, useMemo } from "react"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface HistoryPoint {
  run_date: string
  bb_price_gbp: number | null
  box_pct: number | null
  decision_score: number | null
}

interface CardPricePoint {
  week: string
  avg_market_usd: number
  product_count: number
}

interface DailyPricePoint {
  date: string
  avg_market_usd: number
  product_count: number
}

interface BBDailyPoint {
  date: string
  price_usd: number
  price_gbp: number
}

type RangeKey = "1D" | "1W" | "1M" | "1Y" | "All"
const RANGES: RangeKey[] = ["1D", "1W", "1M", "1Y", "All"]

interface Props {
  history: HistoryPoint[]
  cardPriceHistory: CardPricePoint[]
  cardPriceDailyHistory?: DailyPricePoint[]
  bbDailyHistory?: BBDailyPoint[]
  setName: string
  sparseHistory?: boolean
}

function fmtMonth(d: string): string {
  const [y, m] = d.split("-")
  const months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
  return `${months[parseInt(m)]} '${y.slice(2)}`
}

function fmtDateFull(d: string): string {
  const date = new Date(d + "T00:00:00Z")
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
  return `${months[date.getUTCMonth()]} ${date.getUTCDate()}, ${date.getUTCFullYear()}`
}

function fmtDateShort(d: string): string {
  const date = new Date(d + "T00:00:00Z")
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
  return `${date.getUTCDate()} ${months[date.getUTCMonth()]}`
}

function fmtMonthYear(d: string): string {
  const date = new Date(d + "T00:00:00Z")
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
  return `${months[date.getUTCMonth()]} '${String(date.getUTCFullYear()).slice(2)}`
}

function cutoffDate(range: RangeKey, latestDate: string): Date {
  const latest = new Date(latestDate + "T00:00:00Z")
  switch (range) {
    case "1D": { const d = new Date(latest); d.setUTCDate(d.getUTCDate() - 1); return d }
    case "1W": { const d = new Date(latest); d.setUTCDate(d.getUTCDate() - 7); return d }
    case "1M": { const d = new Date(latest); d.setUTCMonth(d.getUTCMonth() - 1); return d }
    case "1Y": { const d = new Date(latest); d.setUTCFullYear(d.getUTCFullYear() - 1); return d }
    case "All": return new Date("2000-01-01")
  }
}

function filterByRange<T extends { date: string }>(data: T[], range: RangeKey): T[] {
  if (data.length === 0) return []
  const latest = data[data.length - 1].date
  const cutoff = cutoffDate(range, latest)
  const filtered = data.filter(p => new Date(p.date + "T00:00:00Z") > cutoff)
  if (range === "1D" && filtered.length < 2) return data.slice(-2)
  return filtered.length >= 1 ? filtered : data.slice(-2)
}

function xInterval(n: number): number {
  if (n <= 7) return 0
  if (n <= 14) return 1
  if (n <= 31) return Math.floor(n / 6)
  return Math.floor(n / 8)
}

function xTickFmt(range: RangeKey) {
  return (v: string) => {
    if (range === "1D" || range === "1W" || range === "1M") return fmtDateShort(v)
    return fmtMonthYear(v)
  }
}

const BBTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  const usd = payload.find((p: any) => p.dataKey === "price_usd")?.value
  const gbp = payload.find((p: any) => p.dataKey === "price_gbp")?.value
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      {gbp != null && <p className="text-white text-sm font-semibold">£{Number(gbp).toFixed(2)}</p>}
      {usd != null && <p className="text-slate-400 text-xs">${Number(usd).toFixed(2)} USD</p>}
    </div>
  )
}

const CardTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      <p className="text-white text-sm font-semibold">${Number(payload[0].value).toFixed(2)}</p>
    </div>
  )
}

interface StockChartProps {
  data: any[]
  range: RangeKey
  onRangeChange: (r: RangeKey) => void
  currentPrice: string
  priceLabel: string
  change: number
  changePct: string | null
  dataKey: string
  dataKey2?: string
  color: string
  tooltipComponent: any
  dataNote?: string
  sparseNote?: boolean
}

function StockChart({
  data, range, onRangeChange, currentPrice, priceLabel,
  change, changePct, dataKey, dataKey2, color, tooltipComponent, dataNote, sparseNote
}: StockChartProps) {
  const isUp = change >= 0
  const lineColor = isUp ? "#34d399" : "#f87171"
  const gradId = isUp ? "gradUp_" + dataKey : "gradDown_" + dataKey

  return (
    <>
      {/* Header row: label + change badge */}
      <div className="flex items-start justify-between mb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-slate-400 text-xs uppercase tracking-wider">{priceLabel}</p>
          {sparseNote && (
            <span className="text-xs text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">Limited data</span>
          )}
        </div>
        {changePct && (
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`text-sm font-bold ${isUp ? "text-emerald-400" : "text-red-400"}`}>
              {isUp ? "+" : ""}{changePct}%
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${isUp ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
              {range}
            </span>
          </div>
        )}
      </div>

      {/* Range buttons */}
      <div className="flex gap-1 mb-3">
        {RANGES.map(r => (
          <button
            key={r}
            onClick={() => onRangeChange(r)}
            className={`text-xs font-medium px-2.5 py-1 rounded-md transition-all ${
              range === r
                ? "bg-slate-700 text-white"
                : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Current price */}
      <div className="mb-3">
        <span className="text-2xl font-bold text-white">{currentPrice}</span>
        {change !== 0 && changePct && (
          <span className={`ml-2 text-sm ${isUp ? "text-emerald-400" : "text-red-400"}`}>
            {isUp ? "▲" : "▼"} {Math.abs(change).toFixed(2)} ({isUp ? "+" : ""}{changePct}%)
          </span>
        )}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={lineColor} stopOpacity={0.18} />
              <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            interval={xInterval(data.length)}
            tickFormatter={xTickFmt(range)}
          />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip content={tooltipComponent} />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={lineColor}
            strokeWidth={2}
            fill={`url(#${gradId})`}
            dot={false}
            activeDot={{ r: 5, fill: lineColor, stroke: "#1e293b", strokeWidth: 2 }}
            animationDuration={350}
          />
          {/* invisible second series to populate tooltip with dual values */}
          {dataKey2 && (
            <Area
              type="monotone"
              dataKey={dataKey2}
              stroke="none"
              fill="none"
              dot={false}
              activeDot={false}
              animationDuration={350}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>

      {dataNote && (
        <p className="text-slate-700 text-xs mt-2 text-right">{dataNote}</p>
      )}
    </>
  )
}

export function SetPageClient({
  history,
  cardPriceHistory,
  cardPriceDailyHistory = [],
  bbDailyHistory = [],
  setName,
  sparseHistory = false,
}: Props) {
  const [bbRange, setBBRange] = useState<RangeKey>("All")
  const [cardRange, setCardRange] = useState<RangeKey>("All")

  // ── Monthly BB data (fallback for sets with no daily data) ────────────────
  const bbMonthly = history
    .filter(h => h.bb_price_gbp != null)
    .map(h => ({
      month: fmtMonth(h.run_date),
      price: h.bb_price_gbp,
      boxPct: h.box_pct != null ? Math.round(h.box_pct * 1000) / 10 : null,
      score: h.decision_score,
    }))

  // ── Daily BB data (preferred) ─────────────────────────────────────────────
  const allBBDaily = useMemo(() =>
    bbDailyHistory.map(p => ({
      date: p.date,
      price_gbp: p.price_gbp,
      price_usd: p.price_usd,
      label: fmtDateFull(p.date),
    })),
    [bbDailyHistory]
  )
  const hasBBDaily = allBBDaily.length >= 2

  const filteredBB = useMemo(() => filterByRange(allBBDaily, bbRange), [allBBDaily, bbRange])

  const bbFirst = filteredBB[0]?.price_gbp ?? 0
  const bbLast = filteredBB[filteredBB.length - 1]?.price_gbp ?? 0
  const bbChange = bbLast - bbFirst
  const bbChangePct = bbFirst > 0 ? ((bbChange / bbFirst) * 100).toFixed(2) : null

  // ── Daily Card index data ─────────────────────────────────────────────────
  const allCardDaily = useMemo(() => {
    const src = cardPriceDailyHistory.length >= 2 ? cardPriceDailyHistory.map(p => ({
      date: p.date, avg: p.avg_market_usd, label: fmtDateFull(p.date),
    })) : cardPriceHistory.map(p => ({
      date: p.week, avg: p.avg_market_usd, label: fmtDateFull(p.week),
    }))
    return src
  }, [cardPriceDailyHistory, cardPriceHistory])

  const hasCardDaily = allCardDaily.length >= 2
  const filteredCard = useMemo(() => filterByRange(allCardDaily, cardRange), [allCardDaily, cardRange])

  const cardFirst = filteredCard[0]?.avg ?? 0
  const cardLast = filteredCard[filteredCard.length - 1]?.avg ?? 0
  const cardChange = cardLast - cardFirst
  const cardChangePct = cardFirst > 0 ? ((cardChange / cardFirst) * 100).toFixed(2) : null

  return (
    <div>
      {/* ── BB Price chart ─────────────────────────────────────────────────── */}
      {hasBBDaily ? (
        <StockChart
          data={filteredBB}
          range={bbRange}
          onRangeChange={setBBRange}
          currentPrice={`£${bbLast.toFixed(2)}`}
          priceLabel="Booster Box Price (GBP)"
          change={bbChange}
          changePct={bbChangePct}
          dataKey="price_gbp"
          dataKey2="price_usd"
          color="#60a5fa"
          tooltipComponent={<BBTooltip />}
          dataNote={`${filteredBB.length} daily data points · TCGPlayer via TCGCSV`}
          sparseNote={sparseHistory && bbRange === "All"}
        />
      ) : bbMonthly.length >= 2 ? (
        /* fallback: old monthly chart */
        <>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <p className="text-slate-400 text-xs uppercase tracking-wider">BB Price (GBP) — Monthly</p>
              {sparseHistory && (
                <span className="text-xs text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded">Limited data</span>
              )}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={120}>
            <AreaChart data={bbMonthly} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="bbGradFallback" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.18} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis hide domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(v: any) => [`£${Number(v).toFixed(2)}`, "BB Price"]}
              />
              <Area type="monotone" dataKey="price" stroke="#60a5fa" strokeWidth={2} fill="url(#bbGradFallback)" dot={{ fill: "#60a5fa", r: 3 }} activeDot={{ r: 5 }} />
            </AreaChart>
          </ResponsiveContainer>
        </>
      ) : (
        <div className="h-32 flex flex-col items-center justify-center gap-1">
          <span className="text-slate-500 text-sm">Not enough history yet for {setName}</span>
          <span className="text-slate-600 text-xs">Price history builds as new data is collected</span>
        </div>
      )}

      {/* ── Box % Trend (monthly, always shown if data exists) ────────────── */}
      {bbMonthly.length >= 2 && (
        <div className="mt-5">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">Box % Trend — Monthly</p>
          <ResponsiveContainer width="100%" height={80}>
            <AreaChart data={bbMonthly} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="boxPctGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#34d399" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis hide domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(v: any) => [`${Number(v).toFixed(1)}%`, "Box %"]}
              />
              <Area type="monotone" dataKey="boxPct" stroke="#34d399" strokeWidth={2} fill="url(#boxPctGradient)" dot={{ fill: "#34d399", r: 3 }} activeDot={{ r: 5 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Card Market Index ─────────────────────────────────────────────── */}
      <div className="mt-6 pt-5 border-t border-slate-700/50">
        {hasCardDaily ? (
          <StockChart
            data={filteredCard}
            range={cardRange}
            onRangeChange={setCardRange}
            currentPrice={`$${cardLast.toFixed(2)}`}
            priceLabel="Card Market Index (USD)"
            change={cardChange}
            changePct={cardChangePct}
            dataKey="avg"
            color="#f59e0b"
            tooltipComponent={<CardTooltip />}
            dataNote={`${filteredCard.length} data points · TCGPlayer via TCGCSV`}
          />
        ) : (
          <div className="h-20 flex items-center justify-center text-slate-600 text-xs">
            Card price history building — check back soon
          </div>
        )}
      </div>

      {/* ── AI Score history pills ────────────────────────────────────────── */}
      {bbMonthly.some(d => d.score != null) && (
        <div className="flex gap-2 mt-4 flex-wrap">
          {bbMonthly.map(d => (
            <div key={d.month} className="flex-1 min-w-[60px] bg-slate-800 rounded-lg p-2 text-center">
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
