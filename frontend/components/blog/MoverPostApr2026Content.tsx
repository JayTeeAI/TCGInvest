import Link from "next/link"

function GainRow({ name, slug, prev, curr, pct, rec }: { name: string; slug: string; prev: number; curr: number; pct: number; rec: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
      <div>
        <Link href={`/sets/${slug}`} className="text-white font-medium text-sm hover:text-blue-400 transition-colors">{name}</Link>
        <p className="text-slate-500 text-xs mt-0.5">{rec}</p>
      </div>
      <div className="text-right">
        <p className="text-emerald-400 font-bold text-sm">+{pct}%</p>
        <p className="text-slate-500 text-xs">£{prev.toLocaleString()} &rarr; £{curr.toLocaleString()}</p>
      </div>
    </div>
  )
}

function DropRow({ name, slug, prev, curr, pct, rec }: { name: string; slug: string; prev: number; curr: number; pct: number; rec: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
      <div>
        <Link href={`/sets/${slug}`} className="text-white font-medium text-sm hover:text-blue-400 transition-colors">{name}</Link>
        <p className="text-slate-500 text-xs mt-0.5">{rec}</p>
      </div>
      <div className="text-right">
        <p className="text-red-400 font-bold text-sm">{pct}%</p>
        <p className="text-slate-500 text-xs">£{prev.toLocaleString()} &rarr; £{curr.toLocaleString()}</p>
      </div>
    </div>
  )
}

export function MoverPostApr2026Content() {
  return (
    <div>
      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">Overview</h2>
        <p className="text-slate-300 leading-relaxed mb-4">
          April 2026 vs March 2026 comparison across 43 tracked booster box sets.
          Data sourced from eBay UK sold listings via TCGInvest monthly price pipeline.
        </p>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">&#x1F680; Biggest Gainers</h2>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <GainRow name="Prismatic Evolutions" slug="prismatic-evolutions" prev={280.0} curr={938.6} pct={235.2} rec="Accumulate" />
          <GainRow name="151" slug="151" prev={780.0} curr={2214.14} pct={183.9} rec="Overvalued" />
          <GainRow name="Paldean Fates" slug="paldean-fates" prev={800.0} curr={1470.72} pct={83.8} rec="Accumulate" />
          <GainRow name="Ascended Hereos" slug="ascended-hereos" prev={280.0} curr={451.22} pct={61.2} rec="Accumulate" />
          <GainRow name="Silver Tempest" slug="silver-tempest" prev={260.0} curr={413.65} pct={59.1} rec="Strong Buy" />
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">&#x1F4C9; Biggest Drops</h2>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <DropRow name="Lost Thunder" slug="lost-thunder" prev={1757.0} curr={1372.18} pct={-21.9} rec="Hold" />
          <DropRow name="Ultra Prism" slug="ultra-prism" prev={1671.0} curr={1331.18} pct={-20.3} rec="Hold" />
          <DropRow name="S&V Base set" slug="sandv-base-set" prev={255.0} curr={225.62} pct={-11.5} rec="Accumulate" />
          <DropRow name="Mega Evolution (Enhanced)" slug="mega-evolution-enhanced" prev={270.0} curr={240.67} pct={-10.9} rec="Strong Buy" />
          <DropRow name="Sword and Shield" slug="sword-and-shield" prev={665.0} curr={592.64} pct={-10.9} rec="Overvalued" />
        </div>
      </div>

      <p className="text-slate-500 text-xs mt-6">
        Comparison period: March 2026 vs April 2026.
        Prices from eBay UK sold listings. AI scores via Groq llama-3.3-70b.
        Next update: following monthly pipeline run.
      </p>
    </div>
  )
}
