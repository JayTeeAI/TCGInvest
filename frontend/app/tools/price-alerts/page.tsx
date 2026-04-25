'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Alert {
  id: number
  product_type: 'set' | 'etb' | 'chase_card'
  product_id: number
  product_name: string
  threshold_gbp: number
  triggered: boolean
  triggered_at: string | null
  created_at: string
}

const PRODUCT_LABEL: Record<string, string> = {
  set: 'Booster Box',
  etb: 'ETB',
  chase_card: 'Chase Card',
}

const PRODUCT_EMOJI: Record<string, string> = {
  set: '📦',
  etb: '🎁',
  chase_card: '✨',
}

export default function PriceAlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState<number | null>(null)
  const [role, setRole] = useState<string>('free')

  useEffect(() => {
    Promise.all([
      fetch('/auth/me', { credentials: 'include' }).then(r => r.json()),
      fetch('/api/alerts', { credentials: 'include' })
    ]).then(async ([me, alertsRes]) => {
      if (alertsRes.status === 401) { setError('unauth'); setLoading(false); return }
      setRole(me.role || 'free')
      const d = await alertsRes.json()
      setAlerts(d)
      setLoading(false)
    }).catch(() => { setError('failed'); setLoading(false) })
  }, [])

  const deleteAlert = async (id: number) => {
    setDeleting(id)
    await fetch(`/api/alerts/${id}`, { method: 'DELETE', credentials: 'include' })
    setAlerts(prev => prev.filter(a => a.id !== id))
    setDeleting(null)
  }

  if (loading) return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <p className="text-slate-400">Loading alerts…</p>
    </main>
  )

  if (error === 'unauth') return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center">
        <p className="text-4xl mb-3">🔔</p>
        <p className="text-slate-300 font-medium mb-2">Sign in to manage price alerts</p>
        <p className="text-slate-500 text-sm mb-5">Get emailed when a product drops below your target price.</p>
        <a href="/auth/google" className="bg-white text-slate-900 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-slate-100 transition-colors">Sign in with Google — it's free</a>
      </div>
    </main>
  )

  const active = alerts.filter(a => !a.triggered)
  const fired = alerts.filter(a => a.triggered)
  const isPremium = role === 'premium' || role === 'admin'

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">

        <div className="flex items-center gap-2 text-sm text-slate-500 mb-6">
          <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
          <span>›</span>
          <span className="text-slate-300">Price Alerts</span>
        </div>

        <h1 className="text-2xl font-bold text-white mb-1">Price Alerts</h1>
        <p className="text-slate-400 text-sm mb-6">
          Get emailed when a product drops below your target price. One email per alert, then it deactivates.
        </p>

        {/* How-to guide */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-8">
          <p className="text-slate-300 font-semibold text-sm mb-3">How it works</p>
          <ol className="space-y-2">
            <li className="flex gap-3 text-sm text-slate-400">
              <span className="bg-slate-800 text-slate-300 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0">1</span>
              <span>Browse to any <Link href="/tools/tracker" className="text-blue-400 hover:text-blue-300">booster box</Link>, <Link href="/tools/etb-tracker" className="text-blue-400 hover:text-blue-300">ETB</Link>, or <Link href="/tools/chase-cards" className="text-blue-400 hover:text-blue-300">chase card</Link> set page.</span>
            </li>
            <li className="flex gap-3 text-sm text-slate-400">
              <span className="bg-slate-800 text-slate-300 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0">2</span>
              <span>Click the 🔔 bell icon and enter your target price threshold.</span>
            </li>
            <li className="flex gap-3 text-sm text-slate-400">
              <span className="bg-slate-800 text-slate-300 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0">3</span>
              <span>We email you at <strong className="text-slate-300">{/* email shown below */}your registered address</strong> when the price drops to or below your threshold.</span>
            </li>
          </ol>
          <div className="mt-4 pt-4 border-t border-slate-800 flex gap-2 flex-wrap">
            <Link href="/tools/tracker" className="text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition-colors">📦 Booster Boxes</Link>
            <Link href="/tools/etb-tracker" className="text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition-colors">🎁 ETB Tracker</Link>
            <Link href="/tools/chase-cards" className="text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition-colors">✨ Chase Cards</Link>
          </div>
        </div>

        {!isPremium && (
          <div className="mb-6 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl flex items-start gap-3">
            <span className="text-yellow-400 text-lg shrink-0">⚡</span>
            <div>
              <p className="text-yellow-300 font-medium text-sm">Free plan: 1 active alert</p>
              <p className="text-slate-400 text-xs mt-0.5">
                <a href="/premium" className="text-yellow-400 hover:text-yellow-300 underline">Upgrade to Premium</a> for unlimited alerts across all product types.
              </p>
            </div>
          </div>
        )}

        {active.length === 0 && fired.length === 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
            <p className="text-4xl mb-3">🔔</p>
            <p className="text-slate-300 font-medium mb-1">No alerts set yet</p>
            <p className="text-slate-500 text-sm">Browse a set or card page and click the bell icon to set your first alert.</p>
          </div>
        )}

        {active.length > 0 && (
          <div className="mb-6">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Active ({active.length})</h2>
            <div className="space-y-2">
              {active.map(alert => (
                <div key={alert.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between gap-4">
                  <div className="min-w-0 flex items-center gap-2">
                    <span className="text-base shrink-0">{PRODUCT_EMOJI[alert.product_type] ?? '🔔'}</span>
                    <div className="min-w-0">
                      <p className="text-white font-medium text-sm truncate">{alert.product_name}</p>
                      <p className="text-slate-500 text-xs mt-0.5">
                        Alert below <span className="text-slate-300 font-medium">£{Number(alert.threshold_gbp).toFixed(2)}</span>
                        {' · '}{PRODUCT_LABEL[alert.product_type] ?? alert.product_type}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => deleteAlert(alert.id)}
                    disabled={deleting === alert.id}
                    className="text-slate-600 hover:text-red-400 transition-colors text-xs shrink-0 disabled:opacity-40"
                  >
                    {deleting === alert.id ? 'Removing…' : 'Remove'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {fired.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Triggered ({fired.length})</h2>
            <div className="space-y-2">
              {fired.map(alert => (
                <div key={alert.id} className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4 flex items-center justify-between gap-4 opacity-60">
                  <div className="min-w-0 flex items-center gap-2">
                    <span className="text-base shrink-0">{PRODUCT_EMOJI[alert.product_type] ?? '🔔'}</span>
                    <div className="min-w-0">
                      <p className="text-slate-300 font-medium text-sm truncate">{alert.product_name}</p>
                      <p className="text-slate-500 text-xs mt-0.5">
                        Triggered at £{Number(alert.threshold_gbp).toFixed(2)}
                        {alert.triggered_at ? ` · ${new Date(alert.triggered_at).toLocaleDateString('en-GB')}` : ''}
                      </p>
                    </div>
                  </div>
                  <span className="text-green-500 text-xs shrink-0">✓ Sent</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-slate-800 text-center">
          <a href="/account/preferences" className="text-slate-600 hover:text-slate-400 text-xs transition-colors">
            ⚙️ Manage email preferences
          </a>
        </div>

      </div>
    </main>
  )
}
