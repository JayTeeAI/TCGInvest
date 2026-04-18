"use client"
import Link from "next/link"

export default function PremiumCancel() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <p className="text-4xl mb-6">👋</p>
        <h1 className="text-2xl font-bold text-white mb-4">No worries</h1>
        <p className="text-slate-400 mb-8">You can upgrade to Premium any time from the tracker page.</p>
        <Link
          href="/tools/tracker"
          className="inline-block bg-slate-700 text-white font-medium px-6 py-3 rounded-xl hover:bg-slate-600 transition-colors"
        >
          Back to tracker
        </Link>
      </div>
    </main>
  )
}
