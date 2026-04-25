'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Disclaimer } from '@/components/Disclaimer'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

interface RoiSet {
  id: number
  name: string
  era: string
  logo_url: string | null
}

interface SeriesPoint {
  date: string
  portfolio_gbp: number
  sp500_gbp: number
}

interface RoiResult {
  set_name: string
  set_id: number
  purchase_date: string
  used_earliest_date: boolean
  quantity: number
  purchase_value_gbp: number
  current_value_gbp: number
  current_price_gbp: number
  abs_gain_gbp: number
  pct_return: number
  ann_return: number
  years_held: number
  sp500_value_gbp: number
  sp500_gain_gbp: number
  fx_rate: number
  series: SeriesPoint[]
}

function formatGBP(v: number | null) {
  if (v === null) return '—'
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(v)
}

function formatPct(v: number | null) {
  if (v === null) return '—'
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })
}

// Thin down series for chart readability (max ~52 points)
function thinSeries(series: SeriesPoint[], maxPoints = 52): SeriesPoint[] {
  if (series.length <= maxPoints) return series
  const step = Math.ceil(series.length / maxPoints)
  const thinned = series.filter((_, i) => i % step === 0)
  // Always include last
  if (thinned[thinned.length - 1] !== series[series.length - 1]) {
    thinned.push(series[series.length - 1])
  }
  return thinned
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  color: string;
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipPayloadItem[]; label?: string }) => {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-xl text-sm">
      <p className="text-slate-400 mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name}: {formatGBP(p.value)}
        </p>
      ))}
    </div>
  )
}

export default function RoiCalculatorPage() {
  const [sets, setSets] = useState<RoiSet[]>([])
  const [selectedSetId, setSelectedSetId] = useState<number | ''>('')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [quantity, setQuantity] = useState('1')

  const [loading, setLoading] = useState(false)
  const [setsLoading, setSetsLoading] = useState(true)
  const [error, setError] = useState('')
  const [result, setResult] = useState<RoiResult | null>(null)

  // Load sets with tcgcsv data
  useEffect(() => {
    fetch(`${API_BASE}/api/roi/sets`)
      .then(r => r.json())
      .then(d => setSets(d.sets || []))
      .catch(() => setError('Could not load sets'))
      .finally(() => setSetsLoading(false))
  }, [])

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setResult(null)

    if (!selectedSetId) { setError('Please select a set'); return }
    if (!purchasePrice || parseFloat(purchasePrice) <= 0) { setError('Please enter a valid purchase price'); return }
    if (!purchaseDate) { setError('Please enter a purchase date'); return }
    if (!quantity || parseInt(quantity) < 1) { setError('Please enter a valid quantity'); return }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/roi/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          set_id: selectedSetId,
          purchase_date: purchaseDate,
          purchase_price_gbp: parseFloat(purchasePrice),
          quantity: parseInt(quantity),
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Calculation failed')
        return
      }
      const data: RoiResult = await res.json()
      setResult(data)
    } catch {
      setError('Network error — please try again')
    } finally {
      setLoading(false)
    }
  }

  const isGain = result ? result.abs_gain_gbp >= 0 : true
  const beatsSP500 = result ? result.pct_return > (result.sp500_value_gbp / result.purchase_value_gbp - 1) * 100 : false
  const chartData = result ? thinSeries(result.series) : []

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-12">
        {/* Nav */}
        <div className="mb-8">
          <Link href="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
            ← Back to tools
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">ROI Calculator</h1>
          <p className="text-slate-400">
            See how your sealed Pokémon TCG investment has performed — with historical prices and a benchmark comparison.
          </p>
        </div>

        <Disclaimer />

        {/* Form */}
        <div className="mt-8 bg-slate-900 rounded-xl border border-slate-800 p-6">
          <h2 className="text-xl font-bold mb-6 text-white">Your Investment</h2>
          <form onSubmit={handleCalculate}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Set selector */}
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Pokémon TCG Set
                </label>
                <select
                  value={selectedSetId}
                  onChange={e => setSelectedSetId(e.target.value ? parseInt(e.target.value) : '')}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 appearance-none"
                  disabled={setsLoading}
                >
                  <option value="">{setsLoading ? 'Loading sets…' : '— Select a set —'}</option>
                  {sets.map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.era})</option>
                  ))}
                </select>
                <p className="text-slate-500 text-xs mt-1.5">Only sets with daily price history (TCGCSV) are shown</p>
              </div>

              {/* Purchase price */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Total Purchase Price (£)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 240.00"
                  step="0.01"
                  min="0.01"
                  value={purchasePrice}
                  onChange={e => setPurchasePrice(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Quantity (boxes)
                </label>
                <input
                  type="number"
                  placeholder="1"
                  step="1"
                  min="1"
                  value={quantity}
                  onChange={e => setQuantity(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Purchase date */}
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Purchase Date
                </label>
                <input
                  type="date"
                  value={purchaseDate}
                  onChange={e => setPurchaseDate(e.target.value)}
                  min="2024-02-08"
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-blue-500"
                />
                <p className="text-slate-500 text-xs mt-1.5">
                  Price history available from <span className="text-slate-400">8 Feb 2024</span>. Earlier dates will use the earliest available price.
                </p>
              </div>
            </div>

            {error && (
              <div className="mt-4 text-red-400 text-sm bg-red-950/40 border border-red-900 rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || setsLoading}
              className="mt-6 w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-colors text-base"
            >
              {loading ? 'Calculating…' : 'Calculate ROI'}
            </button>
          </form>
        </div>

        {/* Results */}
        {result && (
          <div className="mt-8 space-y-6">
            {/* Warning if earliest date was used */}
            {result.used_earliest_date && (
              <div className="bg-amber-950/40 border border-amber-800 rounded-lg px-4 py-3 text-amber-300 text-sm">
                ⚠ Your purchase date was before our earliest data (8 Feb 2024). The calculation uses the earliest available price as a proxy.
              </div>
            )}

            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Current Value" value={formatGBP(result.current_value_gbp)} color="text-white" />
              <StatCard
                label="Gain / Loss"
                value={formatGBP(result.abs_gain_gbp)}
                color={isGain ? 'text-green-400' : 'text-red-400'}
              />
              <StatCard
                label="Total Return"
                value={formatPct(result.pct_return)}
                color={isGain ? 'text-green-400' : 'text-red-400'}
              />
              <StatCard
                label="Annualised"
                value={formatPct(result.ann_return)}
                color={result.ann_return >= 0 ? 'text-green-400' : 'text-red-400'}
              />
            </div>

            {/* S&P 500 comparison */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">vs S&amp;P 500 Benchmark (10% p.a.)</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <CompareRow
                  label="Your portfolio"
                  value={formatGBP(result.current_value_gbp)}
                  gain={formatGBP(result.abs_gain_gbp)}
                  positive={isGain}
                />
                <CompareRow
                  label="S&P 500 equivalent"
                  value={formatGBP(result.sp500_value_gbp)}
                  gain={formatGBP(result.sp500_gain_gbp)}
                  positive={true}
                />
                <div className="flex flex-col justify-center">
                  <p className="text-xs text-slate-400 mb-1">Verdict</p>
                  <p className={`text-lg font-bold ${beatsSP500 ? 'text-green-400' : 'text-red-400'}`}>
                    {beatsSP500 ? '✓ Beat the market' : '✗ Underperformed'}
                  </p>
                  <p className="text-slate-400 text-xs mt-1">
                    Held for {result.years_held < 1
                      ? `${Math.round(result.years_held * 12)} months`
                      : `${result.years_held.toFixed(1)} years`}
                  </p>
                </div>
              </div>
            </div>

            {/* Chart */}
            {chartData.length > 1 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6">Portfolio Value Over Time</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={formatDate}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={{ stroke: '#334155' }}
                      tickLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tickFormatter={v => '£' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v)}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      width={52}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      formatter={(value) => <span style={{ color: '#94a3b8', fontSize: '12px' }}>{value}</span>}
                    />
                    <Line
                      type="monotone"
                      dataKey="portfolio_gbp"
                      name="Your Portfolio"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: '#3b82f6' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="sp500_gbp"
                      name="S&P 500 (10% p.a.)"
                      stroke="#f59e0b"
                      strokeWidth={1.5}
                      strokeDasharray="5 4"
                      dot={false}
                      activeDot={{ r: 4, fill: '#f59e0b' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <p className="text-slate-600 text-xs mt-3 text-center">
                  Price data from TCGCSV · USD converted at live rate ({result.fx_rate}) · Past performance is not indicative of future results
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl sm:text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function CompareRow({ label, value, gain, positive }: { label: string; value: string; gain: string; positive: boolean }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-lg font-bold text-white">{value}</p>
      <p className={`text-sm font-medium ${positive ? 'text-green-400' : 'text-red-400'}`}>{gain}</p>
    </div>
  )
}
