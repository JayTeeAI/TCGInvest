"use client"
import Link from "next/link"
import { useEffect } from "react"

export default function PremiumSuccess() {
  useEffect(() => {
    // Could trigger a refresh of user data here
  }, [])

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <p className="text-5xl mb-6">🎉</p>
        <h1 className="text-3xl font-bold text-white mb-4">Welcome to Premium!</h1>
        <p className="text-slate-400 mb-8">You now have access to all TCG Invest Premium features including buy/sell recommendations, score breakdowns, and unlimited watchlist.</p>
        <Link
          href="/tools/tracker"
          className="inline-block bg-yellow-500 text-slate-900 font-semibold px-8 py-3 rounded-xl hover:bg-yellow-400 transition-colors"
        >
          Go to tracker
        </Link>
      </div>
    </main>
  )
}
