"use client"

import { useEffect, useState } from "react"
import { getUserClient } from "@/lib/auth-client"
import Link from "next/link"

interface User {
  authenticated: boolean
  email?: string
  role?: string
}

export default function PremiumPage() {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    getUserClient().then(u => setUser(u.authenticated ? u : null))
  }, [])

  const isLoggedIn = !!user
  const isPremium = user?.role === "premium" || user?.role === "admin"

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <div className="mb-8">
          <Link href="/tools/tracker" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
            ← Back to tracker
          </Link>
        </div>

        <div className="text-center mb-12">
          <p className="text-yellow-500 text-sm font-medium uppercase tracking-wider mb-3">TCG Invest Premium</p>
          <h1 className="text-4xl font-bold text-white mb-4">Make better investment decisions</h1>
          <p className="text-slate-400 text-lg">Everything you need to invest smarter in Pokemon TCG sealed product</p>
        </div>

        {isPremium ? (
          <div className="bg-slate-900 border border-yellow-500/30 rounded-2xl p-8 text-center mb-8">
            <p className="text-2xl mb-3">⭐</p>
            <h2 className="text-white font-bold text-xl mb-2">You are a Premium member</h2>
            <p className="text-slate-400 text-sm mb-6">Thank you for supporting TCG Invest. You have access to all features.</p>
            <ManageButton />
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 text-center mb-8">
            <div className="mb-6">
              <p className="text-5xl font-bold text-white">£3</p>
              <p className="text-slate-400 text-sm mt-1">per month, cancel anytime</p>
            </div>
            {isLoggedIn ? (
              <CheckoutButton />
            ) : (
              <a
                href="/auth/google"
                className="inline-block bg-white text-slate-900 font-semibold px-8 py-3 rounded-xl hover:bg-slate-100 transition-colors"
              >
                Sign in to upgrade
              </a>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          <Feature icon="📊" title="Buy/Sell Recommendations" description="Data-driven recommendations for every set — Strong Buy, Buy, Hold, Reduce, and Sell signals" tier="Premium" />
          <Feature icon="🧠" title="AI Score Breakdown" description="See exactly why each set got its score — Scarcity, Liquidity, Mascot Power and Set Depth explained" tier="Premium" />
          <Feature icon="⭐" title="Unlimited Watchlist" description="Save as many sets as you want to your personal watchlist" tier="Free login" />
          <Feature icon="📅" title="Historical Data" description="Access all monthly snapshots to track price movements over time" tier="Free login" />
          <Feature icon="📈" title="Price Trend Charts" description="See how booster box prices have moved month by month" tier="Free login" />
          <Feature icon="🃏" title="Chase Card Tracking" description="Top 3 chase cards and their contribution to set value" tier="Free" />
        </div>
      </div>
    </main>
  )
}

function Feature({ icon, title, description, tier }: { icon: string; title: string; description: string; tier: string }) {
  const tierColor = tier === "Premium" ? "text-yellow-500" : tier === "Free login" ? "text-blue-400" : "text-slate-400"
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-start gap-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="text-white font-medium text-sm">{title}</p>
          <p className="text-slate-500 text-xs mt-1">{description}</p>
          <p className={`text-xs mt-2 font-medium ${tierColor}`}>{tier}</p>
        </div>
      </div>
    </div>
  )
}

function CheckoutButton() {
  async function handleClick() {
    try {
      const res = await fetch('/api/stripe/checkout', { method: 'POST', credentials: 'include' })
      const data = await res.json()
      if (data.url) {
        window.location.href = data.url
      } else {
        alert('Error: ' + JSON.stringify(data))
      }
    } catch(e) {
      alert('Request failed: ' + e)
    }
  }
  return (
    <button
      onClick={handleClick}
      className="bg-yellow-500 text-slate-900 font-semibold px-8 py-3 rounded-xl hover:bg-yellow-400 transition-colors w-full"
    >
      Upgrade to Premium — £3/month
    </button>
  )
}

function ManageButton() {
  async function handleClick() {
    const res = await fetch('/api/stripe/portal', { method: 'POST', credentials: 'include' })
    const data = await res.json()
    if (data.url) window.location.href = data.url
  }
  return (
    <button
      onClick={handleClick}
      className="bg-slate-700 text-white font-medium px-6 py-2.5 rounded-lg hover:bg-slate-600 transition-colors"
    >
      Manage billing
    </button>
  )
}
