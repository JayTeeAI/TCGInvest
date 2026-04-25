'use client'

import { useState, useEffect } from 'react'

interface SetAlertButtonProps {
  productType: 'set' | 'etb' | 'chase_card'
  productId: number
  productName: string
  currentPrice: number
}

export default function SetAlertButton({ productType, productId, productName, currentPrice }: SetAlertButtonProps) {
  const [open, setOpen] = useState(false)
  const [threshold, setThreshold] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error' | 'limit' | 'unauth' | 'checking'>('checking')
  const [errorMsg, setErrorMsg] = useState('')

  // Check auth state on mount
  useEffect(() => {
    fetch('/auth/me', { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (d.authenticated) setStatus('idle')
        else setStatus('unauth')
      })
      .catch(() => setStatus('unauth'))
  }, [])

  const handleSubmit = async () => {
    const val = parseFloat(threshold)
    if (isNaN(val) || val <= 0) { setErrorMsg('Enter a valid price'); return }
    if (val >= currentPrice) { setErrorMsg(`Must be below current price (£${currentPrice.toFixed(2)})`); return }
    setStatus('loading')
    setErrorMsg('')
    try {
      const res = await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          product_type: productType,
          product_id: productId,
          product_name: productName,
          threshold_gbp: val
        })
      })
      if (res.status === 401) { setStatus('unauth'); return }
      if (res.status === 403) {
        const d = await res.json()
        if (d.detail === 'FREE_LIMIT_REACHED') { setStatus('limit'); return }
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setErrorMsg(d.detail || 'Something went wrong')
        setStatus('idle')
        return
      }
      setStatus('success')
    } catch {
      setErrorMsg('Something went wrong. Please try again.')
      setStatus('idle')
    }
  }

  // Still checking auth
  if (status === 'checking') return null

  // Logged out — show locked state
  if (status === 'unauth') {
    return (
      <div className="flex items-center gap-3 mt-4 p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg">
        <span className="text-slate-500 text-lg">🔔</span>
        <div className="flex-1">
          <p className="text-slate-400 text-sm">Price alerts available after sign in</p>
        </div>
        <a
          href="/auth/google"
          className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded-md transition-colors whitespace-nowrap"
        >
          Sign in free
        </a>
      </div>
    )
  }

  // Alert successfully set
  if (status === 'success') {
    return (
      <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-3">
        <span className="text-green-400">✅</span>
        <p className="text-green-300 text-sm">
          Alert set — we&apos;ll email you when {productName} drops below £{parseFloat(threshold).toFixed(2)}.
        </p>
      </div>
    )
  }

  // Free limit hit
  if (status === 'limit') {
    return (
      <div className="mt-4 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
        <p className="text-amber-300 font-medium text-sm mb-1">Free alert used</p>
        <p className="text-slate-400 text-xs mb-3">Upgrade to Premium for unlimited price alerts across all sets and ETBs.</p>
        <a
          href="/premium"
          className="inline-block bg-amber-500 text-slate-900 px-4 py-1.5 rounded-md font-semibold text-xs hover:bg-amber-400 transition-colors"
        >
          Upgrade to Premium — £3/month
        </a>
      </div>
    )
  }

  // Logged in — idle or loading
  return (
    <div className="mt-4">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 text-sm text-slate-400 border border-slate-700 rounded-lg px-4 py-2 hover:border-slate-500 hover:text-slate-200 transition-colors bg-slate-900"
        >
          <span>🔔</span> Set price alert
        </button>
      ) : (
        <div className="p-4 border border-slate-700 rounded-lg bg-slate-900">
          <p className="text-sm font-medium text-slate-300 mb-3">
            Alert me when <span className="font-semibold text-white">{productName}</span> drops below:
          </p>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-slate-400 text-sm font-medium">£</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder={`e.g. ${(currentPrice * 0.9).toFixed(0)}`}
              value={threshold}
              onChange={e => { setThreshold(e.target.value); setErrorMsg('') }}
              className="bg-slate-800 border border-slate-600 text-slate-100 placeholder-slate-600 rounded-md px-3 py-1.5 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={handleSubmit}
              disabled={status === 'loading'}
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
            >
              {status === 'loading' ? 'Saving…' : 'Set Alert'}
            </button>
            <button
              onClick={() => { setOpen(false); setErrorMsg(''); setStatus('idle') }}
              className="text-slate-600 hover:text-slate-400 text-sm px-1 transition-colors"
            >
              ✕
            </button>
          </div>
          {errorMsg && <p className="text-red-400 text-xs mt-1">{errorMsg}</p>}
          <p className="text-xs text-slate-600 mt-2">
            Current price: £{currentPrice.toFixed(2)} · One email sent, then alert deactivates
          </p>
        </div>
      )}
    </div>
  )
}
