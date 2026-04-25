'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import Link from 'next/link'
import Image from 'next/image'

interface SearchResult {
  product_type: 'set' | 'etb' | 'chase'
  product_id: number
  product_name: string
  display_name: string
  set_name?: string
  logo_url: string | null
  current_price_gbp: number | null
}

interface PortfolioItem {
  id: number
  product_type: 'set' | 'etb' | 'chase'
  product_id: number
  product_name: string
  purchase_price_gbp: number
  quantity: number
  purchase_date: string
  notes: string | null
  current_price_gbp: number | null
  cost_basis_gbp: number
  current_value_gbp: number | null
  gain_gbp: number | null
  gain_pct: number | null
  logo_url?: string | null
}

interface Summary {
  total_invested_gbp: number
  total_current_gbp: number
  total_gain_gbp: number
  total_gain_pct: number
}

const TYPE_LABELS: Record<string, string> = { set: 'Booster Box', etb: 'ETB', chase: 'Chase Card' }
const TYPE_COLOURS: Record<string, string> = {
  set: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  etb: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  chase: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
}

function fmt(n: number) { return '£' + n.toFixed(2) }

function GainBadge({ val, pct }: { val: number | null; pct: number | null }) {
  if (val === null || pct === null) return <span className="text-slate-500 text-sm">—</span>
  const pos = val >= 0
  const sign = pos ? '+' : ''
  return (
    <span className={`text-sm font-medium whitespace-nowrap ${pos ? 'text-green-400' : 'text-red-400'}`}>
      {sign}{fmt(val)}&nbsp;({sign}{pct.toFixed(1)}%)
    </span>
  )
}

function LogoImg({ url, name }: { url: string | null; name: string }) {
  if (!url) return (
    <div className="w-8 h-8 rounded bg-slate-700 flex items-center justify-center text-slate-500 text-xs shrink-0">
      {name.charAt(0)}
    </div>
  )
  return (
    <div className="w-8 h-8 rounded overflow-hidden shrink-0 bg-slate-800 flex items-center justify-center">
      <img src={url} alt={name} className="w-full h-full object-contain" />
    </div>
  )
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

export default function PortfolioClient({ role }: { role: string }) {
  const [items, setItems] = useState<PortfolioItem[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Add form state
  const [showAdd, setShowAdd] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState<SearchResult | null>(null)
  const [quantity, setQuantity] = useState('1')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().split('T')[0])
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)

  // Table state
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editQty, setEditQty] = useState('')
  const [editPrice, setEditPrice] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'set' | 'etb' | 'chase'>('all')
  const [searchFilter, setSearchFilter] = useState('')

  const searchRef = useRef<HTMLDivElement>(null)
  const debouncedQuery = useDebounce(searchQuery, 300)
  const isPremium = role === 'premium' || role === 'admin'

  const loadPortfolio = useCallback(async () => {
    const r = await fetch('/api/portfolio', { credentials: 'include' })
    if (r.status === 401) { setError('unauth'); setLoading(false); return }
    const data = await r.json()
    setItems(data.items ?? [])
    setSummary(data.summary ?? null)
    setLoading(false)
  }, [])

  useEffect(() => { loadPortfolio() }, [loadPortfolio])

  // Search products
  useEffect(() => {
    if (debouncedQuery.length < 2) { setSearchResults([]); setShowDropdown(false); return }
    setSearchLoading(true)
    fetch(`/api/portfolio/search?q=${encodeURIComponent(debouncedQuery)}`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => { setSearchResults(d.results ?? []); setShowDropdown(true); setSearchLoading(false) })
      .catch(() => setSearchLoading(false))
  }, [debouncedQuery])

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function selectProduct(r: SearchResult) {
    setSelectedProduct(r)
    setSearchQuery(r.product_name)
    if (r.current_price_gbp) setPurchasePrice(r.current_price_gbp.toFixed(2))
    setShowDropdown(false)
  }

  function resetForm() {
    setSearchQuery(''); setSelectedProduct(null); setQuantity('1')
    setPurchasePrice(''); setPurchaseDate(new Date().toISOString().split('T')[0])
    setNotes(''); setSaveErr(''); setShowAdd(false); setSearchResults([])
  }

  async function handleAdd() {
    setSaveErr('')
    if (!selectedProduct) { setSaveErr('Please search and select a product first.'); return }
    if (!purchasePrice || parseFloat(purchasePrice) <= 0) { setSaveErr('Enter a valid purchase price.'); return }
    setSaving(true)
    const res = await fetch('/api/portfolio', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_type: selectedProduct.product_type,
        product_id: selectedProduct.product_id,
        product_name: selectedProduct.product_name,
        quantity: parseInt(quantity) || 1,
        purchase_price_gbp: parseFloat(purchasePrice),
        purchase_date: purchaseDate,
        notes: notes || null,
      }),
    })
    setSaving(false)
    if (res.ok) { resetForm(); await loadPortfolio() }
    else {
      const d = await res.json().catch(() => ({}))
      setSaveErr(d.detail === 'PREMIUM_REQUIRED' ? 'Portfolio tracking is a Premium feature.' : (d.detail || 'Failed to add item.'))
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    await fetch(`/api/portfolio/${id}`, { method: 'DELETE', credentials: 'include' })
    await loadPortfolio()
    setDeletingId(null)
  }

  async function handleEdit(id: number) {
    await fetch(`/api/portfolio/${id}`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: parseInt(editQty) || undefined, purchase_price_gbp: parseFloat(editPrice) || undefined }),
    })
    setEditingId(null)
    await loadPortfolio()
  }

  const filteredItems = items.filter(item => {
    const typeOk = filterType === 'all' || item.product_type === filterType
    const nameOk = !searchFilter || item.product_name.toLowerCase().includes(searchFilter.toLowerCase())
    return typeOk && nameOk
  })

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <p className="text-slate-400 animate-pulse">Loading portfolio...</p>
    </div>
  )

  if (error === 'unauth') return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center">
        <p className="text-3xl mb-4">💼</p>
        <p className="text-white font-semibold mb-2">Sign in to view your portfolio</p>
        <p className="text-slate-400 text-sm mb-6">Track your sealed product investments in one place.</p>
        <a href="/auth/google" className="bg-white text-slate-900 px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-slate-100 transition-colors">
          Sign in with Google
        </a>
      </div>
    </div>
  )

  // Free user overlay
  if (!isPremium) return (
    <div className="min-h-screen bg-slate-950 px-4 py-12">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-2">My Portfolio</h1>
        <p className="text-slate-400 mb-8">Track your sealed product investments in one place.</p>
        <div className="relative rounded-2xl overflow-hidden border border-slate-700">
          <div className="blur-sm pointer-events-none select-none p-6 bg-slate-900">
            <div className="grid grid-cols-3 gap-4 mb-6">
              {['Total Invested', 'Current Value', 'Total Gain/Loss'].map(l => (
                <div key={l} className="bg-slate-800 rounded-xl p-4">
                  <p className="text-slate-500 text-xs mb-1">{l}</p>
                  <p className="text-white text-xl font-bold">£---</p>
                </div>
              ))}
            </div>
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="bg-slate-800 rounded-lg h-14" />)}</div>
          </div>
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70">
            <div className="text-center px-6 py-8 bg-slate-900 border border-yellow-500/30 rounded-2xl shadow-2xl max-w-sm mx-4">
              <div className="text-3xl mb-3">💼</div>
              <h2 className="text-white font-bold text-lg mb-2">Portfolio Tracker</h2>
              <p className="text-slate-400 text-sm mb-5">Track cost basis, current value, and unrealised gains across your sealed product investments. Premium only.</p>
              <Link href="/premium" className="inline-block bg-yellow-400 text-slate-900 font-semibold px-6 py-2.5 rounded-xl text-sm hover:bg-yellow-300 transition-colors">
                Upgrade to Premium — £3/mo
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  const totalGainPos = (summary?.total_gain_gbp ?? 0) >= 0

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-12">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">My Portfolio</h1>
            <p className="text-slate-400 text-sm mt-1">Sealed product investment tracker</p>
          </div>
          <button
            onClick={() => setShowAdd(prev => !prev)}
            className="bg-yellow-400 text-slate-900 font-semibold px-4 py-2 rounded-xl text-sm hover:bg-yellow-300 transition-colors"
          >
            + Add Holding
          </button>
        </div>

        {/* Stat cards */}
        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
              <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">Total Invested</p>
              <p className="text-white text-2xl font-bold">{fmt(summary.total_invested_gbp)}</p>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
              <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">Current Value</p>
              <p className="text-white text-2xl font-bold">{fmt(summary.total_current_gbp)}</p>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
              <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">Total Gain / Loss</p>
              <p className={`text-2xl font-bold whitespace-nowrap ${totalGainPos ? 'text-green-400' : 'text-red-400'}`}>
                {totalGainPos ? '+' : ''}{fmt(summary.total_gain_gbp)}&nbsp;
                <span className="text-base font-normal opacity-80">
                  ({totalGainPos ? '+' : ''}{summary.total_gain_pct.toFixed(1)}%)
                </span>
              </p>
            </div>
          </div>
        )}

        {/* ── ADD FORM ── */}
        {showAdd && (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 mb-8">
            <h2 className="text-white font-semibold mb-5">Add Holding</h2>

            {/* Product search */}
            <div className="mb-5" ref={searchRef}>
              <label className="text-slate-400 text-xs block mb-1.5">Search product</label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="e.g. Evolving Skies, Pikachu ex..."
                  value={searchQuery}
                  onChange={e => { setSearchQuery(e.target.value); setSelectedProduct(null) }}
                  onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
                  className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-4 py-3 text-sm placeholder-slate-500 focus:outline-none focus:border-yellow-400/50 transition-colors"
                />
                {searchLoading && (
                  <div className="absolute right-3 top-3 w-5 h-5 border-2 border-slate-500 border-t-yellow-400 rounded-full animate-spin" />
                )}

                {/* Dropdown */}
                {showDropdown && searchResults.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-600 rounded-xl shadow-2xl overflow-hidden">
                    {searchResults.map((r, i) => (
                      <button
                        key={i}
                        onClick={() => selectProduct(r)}
                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-700 transition-colors text-left border-b border-slate-700 last:border-0"
                      >
                        <LogoImg url={r.logo_url} name={r.display_name} />
                        <div className="flex-1 min-w-0">
                          <p className="text-white text-sm font-medium truncate">{r.display_name}</p>
                          {r.set_name && <p className="text-slate-500 text-xs">{r.set_name}</p>}
                        </div>
                        <div className="text-right shrink-0">
                          <span className={`text-xs px-2 py-0.5 rounded-full border ${TYPE_COLOURS[r.product_type]}`}>
                            {TYPE_LABELS[r.product_type]}
                          </span>
                          {r.current_price_gbp && (
                            <p className="text-slate-400 text-xs mt-0.5">{fmt(r.current_price_gbp)}</p>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                {showDropdown && searchResults.length === 0 && debouncedQuery.length >= 2 && !searchLoading && (
                  <div className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-600 rounded-xl px-4 py-3 text-slate-500 text-sm">
                    No products found for &ldquo;{debouncedQuery}&rdquo;
                  </div>
                )}
              </div>

              {/* Selected product confirmation */}
              {selectedProduct && (
                <div className="mt-2 flex items-center gap-3 bg-slate-800/60 border border-yellow-400/20 rounded-xl px-4 py-3">
                  <LogoImg url={selectedProduct.logo_url} name={selectedProduct.display_name} />
                  <div className="flex-1">
                    <p className="text-white text-sm font-medium">{selectedProduct.product_name}</p>
                    <span className={`text-xs px-1.5 py-0.5 rounded border ${TYPE_COLOURS[selectedProduct.product_type]}`}>
                      {TYPE_LABELS[selectedProduct.product_type]}
                    </span>
                  </div>
                  <button onClick={() => { setSelectedProduct(null); setSearchQuery('') }} className="text-slate-500 hover:text-white text-xs transition-colors">✕</button>
                </div>
              )}
            </div>

            {/* Price / qty / date row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="text-slate-400 text-xs block mb-1.5">Purchase price (£ each)</label>
                <input
                  type="number" step="0.01" min="0"
                  placeholder={selectedProduct?.current_price_gbp ? fmt(selectedProduct.current_price_gbp) : 'e.g. 89.99'}
                  value={purchasePrice}
                  onChange={e => setPurchasePrice(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-yellow-400/50"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-1.5">Quantity</label>
                <input
                  type="number" min="1"
                  value={quantity}
                  onChange={e => setQuantity(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-yellow-400/50"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-1.5">Purchase date</label>
                <input
                  type="date"
                  value={purchaseDate}
                  onChange={e => setPurchaseDate(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-yellow-400/50"
                />
              </div>
            </div>

            <div className="mb-5">
              <label className="text-slate-400 text-xs block mb-1.5">Notes (optional)</label>
              <input
                type="text" placeholder="e.g. Bought from local shop"
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:border-yellow-400/50"
              />
            </div>

            {saveErr && <p className="text-red-400 text-sm mb-4">{saveErr}</p>}

            <div className="flex gap-3">
              <button
                onClick={handleAdd} disabled={saving || !selectedProduct}
                className="bg-yellow-400 text-slate-900 font-semibold px-5 py-2.5 rounded-xl text-sm hover:bg-yellow-300 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving...' : 'Add to Portfolio'}
              </button>
              <button onClick={resetForm} className="text-slate-400 hover:text-white text-sm px-4 py-2 transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ── FILTERS (only show if items exist) ── */}
        {items.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <input
              type="text"
              placeholder="Filter holdings..."
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-sm placeholder-slate-500 focus:outline-none focus:border-slate-500 w-48"
            />
            {(['all', 'set', 'etb', 'chase'] as const).map(t => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  filterType === t
                    ? 'bg-yellow-400 text-slate-900 border-yellow-400'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-500'
                }`}
              >
                {t === 'all' ? 'All' : TYPE_LABELS[t]}
              </button>
            ))}
            {items.length > 0 && (
              <span className="text-slate-500 text-xs ml-auto">{filteredItems.length} of {items.length} holdings</span>
            )}
          </div>
        )}

        {/* ── HOLDINGS TABLE ── */}
        {items.length === 0 ? (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-12 text-center">
            <p className="text-slate-400 mb-2">No holdings yet.</p>
            <p className="text-slate-500 text-sm">Click <span className="text-yellow-400">+ Add Holding</span> to track your first investment.</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 text-center">
            <p className="text-slate-500 text-sm">No holdings match your filter.</p>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden">
            {/* Desktop */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left text-slate-500 text-xs uppercase tracking-wider px-5 py-3 font-medium">Product</th>
                    <th className="text-right text-slate-500 text-xs uppercase tracking-wider px-4 py-3 font-medium">Qty</th>
                    <th className="text-right text-slate-500 text-xs uppercase tracking-wider px-4 py-3 font-medium">Paid</th>
                    <th className="text-right text-slate-500 text-xs uppercase tracking-wider px-4 py-3 font-medium">Basis</th>
                    <th className="text-right text-slate-500 text-xs uppercase tracking-wider px-4 py-3 font-medium">Value</th>
                    <th className="text-right text-slate-500 text-xs uppercase tracking-wider px-4 py-3 font-medium">Gain / Loss</th>
                    <th className="px-4 py-3 w-24"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map(item => (
                    <tr key={item.id} className="border-b border-slate-800 hover:bg-slate-800/40 transition-colors">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <LogoImg url={item.logo_url ?? null} name={item.product_name} />
                          <div>
                            <p className="text-white font-medium leading-tight">{item.product_name}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className={`text-xs px-1.5 py-0.5 rounded border ${TYPE_COLOURS[item.product_type]}`}>
                                {TYPE_LABELS[item.product_type]}
                              </span>
                              <span className="text-slate-500 text-xs">{item.purchase_date}</span>
                              {item.notes && <span className="text-slate-600 text-xs italic">{item.notes}</span>}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="text-right px-4 py-4">
                        {editingId === item.id
                          ? <input type="number" min={1} value={editQty} onChange={e => setEditQty(e.target.value)} className="w-16 bg-slate-700 border border-slate-600 text-white rounded px-2 py-1 text-sm text-right" />
                          : <span className="text-slate-300">{item.quantity}</span>}
                      </td>
                      <td className="text-right px-4 py-4">
                        {editingId === item.id
                          ? <input type="number" step="0.01" value={editPrice} onChange={e => setEditPrice(e.target.value)} className="w-24 bg-slate-700 border border-slate-600 text-white rounded px-2 py-1 text-sm text-right" />
                          : <span className="text-slate-300">{fmt(item.purchase_price_gbp)}</span>}
                      </td>
                      <td className="text-right px-4 py-4 text-slate-300">{fmt(item.cost_basis_gbp)}</td>
                      <td className="text-right px-4 py-4 text-slate-300">
                        {item.current_value_gbp !== null ? fmt(item.current_value_gbp) : <span className="text-slate-500">—</span>}
                      </td>
                      <td className="text-right px-4 py-4">
                        <GainBadge val={item.gain_gbp} pct={item.gain_pct} />
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2 justify-end">
                          {editingId === item.id ? (
                            <>
                              <button onClick={() => handleEdit(item.id)} className="text-green-400 hover:text-green-300 text-xs font-medium">Save</button>
                              <button onClick={() => setEditingId(null)} className="text-slate-500 hover:text-white text-xs">Cancel</button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => { setEditingId(item.id); setEditQty(String(item.quantity)); setEditPrice(String(item.purchase_price_gbp)) }}
                                className="text-slate-500 hover:text-yellow-400 text-xs transition-colors"
                              >Edit</button>
                              <button
                                onClick={() => handleDelete(item.id)}
                                disabled={deletingId === item.id}
                                className="text-slate-500 hover:text-red-400 text-xs transition-colors disabled:opacity-40 font-medium"
                              >
                                {deletingId === item.id ? '...' : 'Remove'}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden divide-y divide-slate-800">
              {filteredItems.map(item => (
                <div key={item.id} className="px-4 py-4">
                  <div className="flex items-start gap-3 mb-2">
                    <LogoImg url={item.logo_url ?? null} name={item.product_name} />
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-medium text-sm leading-tight">{item.product_name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-xs px-1.5 py-0.5 rounded border ${TYPE_COLOURS[item.product_type]}`}>
                          {TYPE_LABELS[item.product_type]}
                        </span>
                        <span className="text-slate-500 text-xs">×{item.quantity} · {item.purchase_date}</span>
                      </div>
                    </div>
                    <GainBadge val={item.gain_gbp} pct={item.gain_pct} />
                  </div>
                  <div className="flex gap-4 text-xs text-slate-400 mb-3 ml-11">
                    <span>Paid: <span className="text-white">{fmt(item.purchase_price_gbp)}</span></span>
                    <span>Basis: <span className="text-white">{fmt(item.cost_basis_gbp)}</span></span>
                    {item.current_value_gbp !== null && <span>Now: <span className="text-white">{fmt(item.current_value_gbp)}</span></span>}
                  </div>
                  <div className="flex gap-3 ml-11">
                    <button onClick={() => handleDelete(item.id)} disabled={deletingId === item.id} className="text-red-500 hover:text-red-400 text-xs transition-colors font-medium">
                      {deletingId === item.id ? 'Removing...' : 'Remove'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-slate-600 text-xs mt-6 text-center">
          Current values sourced from TCGPlayer (sets), eBay sold listings (ETBs), and PriceCharting (chase cards). Updated regularly.
        </p>
      </div>
    </div>
  )
}
