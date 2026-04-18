"use client"

export function Disclaimer() {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 mb-8">
      <div className="flex gap-3">
        <span className="text-amber-400 text-lg shrink-0">⚠</span>
        <div>
          <p className="text-slate-300 text-sm font-medium mb-1">
            For informational purposes only
          </p>
          <p className="text-slate-500 text-xs leading-relaxed">
            The data, scores and ratings on this platform are provided for
            informational purposes only and do not constitute financial advice.
            Pokemon TCG sealed product values can go up as well as down.
            Always do your own research before making any investment decisions.
            The site owner accepts no liability for any actions taken based on
            information displayed here.
          </p>
        </div>
      </div>
    </div>
  )
}
