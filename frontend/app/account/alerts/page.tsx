'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Alert {
  id: number
  product_type: 'set' | 'etb'
  product_id: number
  product_name: string
  threshold_gbp: number
  triggered: boolean
  triggered_at: string | null
  created_at: string
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState<number | null>(null)
  const [role, setRole] = useState<string>('free')

  useEffect(() => {
    // Fetch role and alerts in parallel
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
        <p className="text-slate-400 mb-4">Sign in to manage your price alerts</p>
        <a href="/auth/google" className="bg-white text-slate-900 px-4 py-2 rounded-lg text-sm font-medium">Sign in with Google</a>
      </div>
    </main>
  )

  const active = alerts.filter(a => !a.triggered)
  const fired = alerts.filter(a => a.triggered)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-2xl mx-auto px-6 py-12">

        <div className="flex items-center gap-2 text-sm text-slate-500 mb-8">
          <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
          <span>›</span>
          <span className="text-slate-300">Price Alerts</span>
        </div>

        <h1 className="text-2xl font-bold text-white mb-2">Price Alerts</h1>
        <p className="text-slate-400 text-sm mb-8">
          We email you once when a product drops below your threshold, then the alert deactivates.
        </p>

        {active.length === 0 && fired.length === 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
            <p className="text-4xl mb-3">🔔</p>
            <p className="text-slate-300 font-medium mb-1">No alerts set yet</p>
            <p className="text-slate-500 text-sm mb-4">Visit any set or ETB page and click &quot;Set price alert&quot; to get started.</p>
            <div className="flex gap-3 justify-center">
              <Link href="/tools/tracker" className="bg-white text-slate-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-100 transition-colors">Booster Box Tracker</Link>
              <Link href="/tools/etb-tracker" className="bg-slate-800 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-700 transition-colors">ETB Tracker</Link>
            </div>
          </div>
        )}

        {active.length > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Active ({active.length})</h2>
            <div className="space-y-3">
              {active.map(alert => (
                <div key={alert.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <Link
                      href={alert.product_type === 'set' ? `/sets/${alert.product_name.toLowerCase().replace(/s&v/gi,'sandv').replace(/&/g,'and').replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'')}` : `/etbs/${alert.product_name.toLowerCase().replace('pokemon centre ','pc-').replace(/&/g,'and').replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'')}`}
                      className="text-white font-medium text-sm hover:text-blue-400 transition-colors truncate block"
                    >
                      {alert.product_name}
                    </Link>
                    <p className="text-slate-500 text-xs mt-0.5">
                      Alert below <span className="text-slate-300 font-medium">£{Number(alert.threshold_gbp).toFixed(2)}</span>
                      {' · '}{alert.product_type === 'set' ? 'Booster Box' : 'ETB'}
                    </p>
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
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Triggered ({fired.length})</h2>
            <div className="space-y-3">
              {fired.map(alert => (
                <div key={alert.id} className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4 flex items-center justify-between gap-4 opacity-60">
                  <div className="min-w-0">
                    <p className="text-slate-300 font-medium text-sm truncate">{alert.product_name}</p>
                    <p className="text-slate-500 text-xs mt-0.5">
                      Triggered at £{Number(alert.threshold_gbp).toFixed(2)}
                      {alert.triggered_at ? ` · ${new Date(alert.triggered_at).toLocaleDateString('en-GB')}` : ''}
                    </p>
                  </div>
                  <span className="text-green-500 text-xs shrink-0">✓ Sent</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {role !== 'premium' && role !== 'admin' && (
          <div className="mt-10 p-4 bg-slate-900 border border-slate-800 rounded-xl text-sm text-slate-400">
            <p className="font-medium text-slate-300 mb-1">Free plan: 1 active alert</p>
            <p className="text-xs mb-3">Upgrade to Premium for unlimited price alerts across all sets and ETBs.</p>
            <a href="/premium" className="inline-block bg-yellow-500 text-slate-900 px-4 py-2 rounded-lg text-xs font-semibold hover:bg-yellow-400 transition-colors">
              Upgrade to Premium — £3/month
            </a>
          </div>
        )}

      
      <div className="mt-8 text-center">
        <a href="/account/preferences" className="text-gray-500 hover:text-gray-300 text-xs underline">
          ⚙️ Manage email preferences
        </a>
      </div>
</div>
    </main>
  )
}
