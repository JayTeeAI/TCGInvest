'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { getCurrentPrice, getSets, getMovers } from '@/lib/api'
import { formatGBP, formatPct } from '@/lib/format'
import { Disclaimer } from '@/components/Disclaimer'

interface PriceData {
  set_name: string
  era: string
  current_price: number
  run_date: string
}

interface MoversData {
  latest: string
  previous: string
  movers: Array<{
    name: string
    era: string
    curr_bb: number
    bb_change_pct: number | null
  }>
}

export default function RoiCalculatorPage({
  searchParams,
}: {
  searchParams: Promise<{ setName?: string; currentPrice?: string }>
}) {
  const [params, setParams] = useState<{ setName?: string; currentPrice?: string }>({})
  const [setName, setSetName] = useState('')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [quantity, setQuantity] = useState('1')

  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [priceError, setPriceError] = useState('')
  const [moversData, setMoversData] = useState<MoversData | null>(null)
  const [availableSets, setAvailableSets] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  // Results
  const [results, setResults] = useState<{
    currentValue: number | null
    profitLossGbp: number | null
    profitLossPct: number | null
    annualisedReturn: number | null
  } | null>(null)

  // Initialize from search params
  useEffect(() => {
    searchParams.then((p) => {
      setParams(p)
      if (p.setName) setSetName(p.setName)
      if (p.currentPrice) setCurrentPrice(parseFloat(p.currentPrice))
    })
  }, [searchParams])

  // Load available sets and movers on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [setsRes, moversRes] = await Promise.all([
          getSets(),
          getMovers(),
        ])
        setAvailableSets(setsRes.sets?.map((s: any) => s.name) || [])
        setMoversData(moversRes as MoversData)
      } catch (error) {
        console.error('Error loading data:', error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  // Fetch current price when set name changes
  const handleSetNameChange = async (name: string) => {
    setSetName(name)
    setPriceError('')
    setCurrentPrice(null)

    if (name.trim()) {
      try {
        const data = await getCurrentPrice(name) as PriceData
        setCurrentPrice(data.current_price)
      } catch (error) {
        setPriceError(`Could not find pricing data for "${name}"`)
        setCurrentPrice(null)
      }
    }
  }

  // Calculate ROI
  const handleCalculate = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!setName.trim()) {
      alert('Please select a set')
      return
    }
    if (!purchasePrice || parseFloat(purchasePrice) <= 0) {
      alert('Please enter a valid purchase price')
      return
    }
    if (!purchaseDate) {
      alert('Please enter a purchase date')
      return
    }
    if (!quantity || parseFloat(quantity) <= 0) {
      alert('Please enter a valid quantity')
      return
    }
    if (currentPrice === null || currentPrice <= 0) {
      alert('Could not fetch current price for this set')
      return
    }

    const purchasePriceNum = parseFloat(purchasePrice)
    const quantityNum = parseFloat(quantity)

    // Calculate
    const totalCurrentValue = currentPrice * quantityNum
    const profitLoss = totalCurrentValue - purchasePriceNum
    const profitLossPct = (profitLoss / purchasePriceNum) * 100

    // Annualised return
    const purchaseDateObj = new Date(purchaseDate)
    const now = new Date()
    const yearsHeld = (now.getTime() - purchaseDateObj.getTime()) / (365.25 * 24 * 60 * 60 * 1000)
    let annualisedReturn: number | null = null
    if (yearsHeld > 0 && purchasePriceNum > 0) {
      annualisedReturn = (Math.pow(totalCurrentValue / purchasePriceNum, 1 / yearsHeld) - 1) * 100
    }

    setResults({
      currentValue: totalCurrentValue,
      profitLossGbp: profitLoss,
      profitLossPct: profitLossPct,
      annualisedReturn: annualisedReturn,
    })
  }

  const isCurrentSetInMovers = moversData?.movers.some(m => m.name === setName)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-5xl mx-auto px-6 py-12">
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
            Calculate your return on investment for Pokemon TCG sealed products.
          </p>
        </div>

        <Disclaimer />

        {/* Main content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          {/* Input form */}
          <div className="lg:col-span-2">
            <form onSubmit={handleCalculate} className="bg-slate-900 rounded-xl border border-slate-800 p-6">
              <h2 className="text-xl font-bold mb-6 text-white">Your Investment</h2>

              {/* Set Name */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Pokemon TCG Set
                </label>
                <input
                  type="text"
                  placeholder="Search for a set..."
                  value={setName}
                  onChange={(e) => handleSetNameChange(e.target.value)}
                  list="sets-list"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-slate-600"
                />
                <datalist id="sets-list">
                  {availableSets.map((set) => (
                    <option key={set} value={set} />
                  ))}
                </datalist>
                {priceError && <p className="text-red-400 text-sm mt-2">{priceError}</p>}
                {currentPrice && setName && (
                  <p className="text-green-400 text-sm mt-2">
                    Current price: {formatGBP(currentPrice)} per box
                  </p>
                )}
              </div>

              {/* Purchase Price */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Total Purchase Price (£)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 240.00"
                  step="0.01"
                  value={purchasePrice}
                  onChange={(e) => setPurchasePrice(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-slate-600"
                />
              </div>

              {/* Purchase Date */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Purchase Date
                </label>
                <input
                  type="date"
                  value={purchaseDate}
                  onChange={(e) => setPurchaseDate(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-slate-600"
                />
              </div>

              {/* Quantity */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Quantity (boxes)
                </label>
                <input
                  type="number"
                  placeholder="1"
                  step="1"
                  min="1"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-slate-600"
                />
              </div>

              {/* Submit button */}
              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Calculate ROI
              </button>
            </form>
          </div>

          {/* Results */}
          <div>
            {results ? (
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
                <h2 className="text-xl font-bold mb-6 text-white">Results</h2>

                <ResultCard
                  label="Current Value"
                  value={formatGBP(results.currentValue)}
                  color="text-white"
                />

                <ResultCard
                  label="Profit/Loss (£)"
                  value={formatGBP(results.profitLossGbp)}
                  color={results.profitLossGbp && results.profitLossGbp >= 0 ? 'text-green-400' : 'text-red-400'}
                />

                <ResultCard
                  label="Profit/Loss (%)"
                  value={results.profitLossPct != null ? `${results.profitLossPct.toFixed(1)}%` : '—'}
                  color={results.profitLossPct && results.profitLossPct >= 0 ? 'text-green-400' : 'text-red-400'}
                />

                {results.annualisedReturn != null && (
                  <ResultCard
                    label="Annualised Return (%)"
                    value={`${results.annualisedReturn.toFixed(1)}%`}
                    color={results.annualisedReturn >= 0 ? 'text-green-400' : 'text-red-400'}
                  />
                )}
              </div>
            ) : (
              <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 text-center">
                <p className="text-slate-400">Fill in your investment details and click Calculate ROI to see results.</p>
              </div>
            )}
          </div>
        </div>

        {/* Market Movers */}
        {moversData && moversData.movers.length > 0 && (
          <div className="mt-12">
            <h2 className="text-xl font-bold text-white mb-4">Market Movers (Top 3)</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {moversData.movers.slice(0, 3).map((mover) => (
                <div
                  key={mover.name}
                  className={`rounded-xl border p-4 ${
                    isCurrentSetInMovers && mover.name === setName
                      ? 'bg-blue-900 border-blue-700'
                      : 'bg-slate-900 border-slate-800'
                  }`}
                >
                  <p className="font-medium text-white">{mover.name}</p>
                  <p className="text-slate-400 text-sm mb-2">{mover.era}</p>
                  <p className="text-lg font-bold">
                    {mover.curr_bb ? formatGBP(mover.curr_bb) : '—'}
                  </p>
                  {mover.bb_change_pct != null && (
                    <p className={`text-sm font-medium ${
                      mover.bb_change_pct >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {mover.bb_change_pct >= 0 ? '+' : ''}{mover.bb_change_pct.toFixed(1)}% MoM
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

function ResultCard({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: string
}) {
  return (
    <div className="mb-4 pb-4 border-b border-slate-800 last:border-b-0">
      <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
