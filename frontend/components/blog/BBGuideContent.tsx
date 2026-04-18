import Link from "next/link"

interface SetRow {
  rank: number
  name: string
  slug: string
  score: number
  rec: string
  boxPct: number
  price: number
  era: string
  highlight: string
}

const sets: SetRow[] = [
  { rank: 1, name: "Brilliant Stars", slug: "brilliant-stars", score: 20, rec: "Strong Buy", boxPct: 53.3, price: 526.46, era: "SWSH", highlight: "Perfect 20/20 score — Charizard VSTAR chase, strong liquidity, out of print. Box at 53% of set value." },
  { rank: 2, name: "Lost Origin", slug: "lost-origin", score: 19, rec: "Strong Buy", boxPct: 54.1, price: 676.87, era: "SWSH", highlight: "Giratina VSTAR drives strong collector demand. Box % near 54% leaves meaningful upside if Giratina maintains value." },
  { rank: 3, name: "Silver Tempest", slug: "silver-tempest", score: 19, rec: "Strong Buy", boxPct: 46.2, price: 413.65, era: "SWSH", highlight: "Lugia VSTAR — iconic mascot, strong pull rates. Box at 46% of set value is one of the best ratios in the tracker." },
  { rank: 4, name: "Fusion Strike", slug: "fusion-strike", score: 19, rec: "Strong Buy", boxPct: 61.5, price: 902.46, era: "SWSH", highlight: "Mew VMAX chase card. Large set with multiple chase tiers — lower single-card dependency than most." },
  { rank: 5, name: "Mega Evolution (Enhanced)", slug: "mega-evolution-enhanced", score: 19, rec: "Strong Buy", boxPct: 23.6, price: 240.67, era: "S&V", highlight: "Extraordinary box % of 23.6% — cards worth nearly 4x the box price. Mega Charizard X nostalgia factor." },
  { rank: 6, name: "Astral Radiance", slug: "astral-radiance", score: 18, rec: "Strong Buy", boxPct: 43.7, price: 364.76, era: "SWSH", highlight: "Origin Forme Palkia VSTAR. Strong set depth with multiple alt arts. Sub-£400 entry point is accessible." },
  { rank: 7, name: "Crown Zenith", slug: "crown-zenith", score: 19, rec: "Strong Buy", boxPct: 64.5, price: 1052.92, era: "SWSH", highlight: "Galarian Gallery subset is the standout. Premium price but consistently liquid — sells quickly at market." },
  { rank: 8, name: "Chilling Reign", slug: "chilling-reign", score: 17, rec: "Buy", boxPct: 34.9, price: 451.25, era: "SWSH", highlight: "Shadow Rider Calyrex VMAX and Ice Rider give dual chase options. 34.9% box % is strong value." },
  { rank: 9, name: "Evolving Skies", slug: "evolving-skies", score: 19, rec: "Buy", boxPct: 55.0, price: 2619.13, era: "SWSH", highlight: "Umbreon VMAX Alt Art — arguably the most desired card in SWSH era. Long-term OOP, strong collector ceiling." },
  { rank: 10, name: "Vivid Voltage", slug: "vivid-voltage", score: 19, rec: "Strong Buy", boxPct: 68.0, price: 259.47, era: "SWSH", highlight: "Pikachu Amazing Rare. Under £260 entry — accessible price point with strong score for speculative hold." },
]

function RecBadge({ rec }: { rec: string }) {
  const colors: Record<string, string> = {
    "Strong Buy": "bg-green-600 text-white",
    "Buy": "bg-green-900 text-green-300",
    "Accumulate": "bg-blue-900 text-blue-300",
  }
  return <span className={`text-xs font-medium px-2 py-0.5 rounded ${colors[rec] ?? "bg-slate-700 text-slate-300"}`}>{rec}</span>
}

function ScoreDots({ score }: { score: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 20 }).map((_, i) => (
        <div key={i} className={`h-1.5 w-1.5 rounded-full ${i < score ? "bg-blue-400" : "bg-slate-700"}`} />
      ))}
    </div>
  )
}

export function BBGuideContent() {
  return (
    <div>
      <div className="mb-8">
        <p className="text-slate-300 leading-relaxed mb-4">
          Rankings are based on TCG Invest&apos;s AI investment scoring model — four dimensions rated out of 5 each: 
          Scarcity (print run status), Liquidity (ease of resale), Mascot Power (featured Pokémon desirability), 
          and Set Depth (breadth of valuable cards). Maximum score is 20/20.
        </p>
        <p className="text-slate-300 leading-relaxed mb-4">
          Box % (booster box price ÷ total set value) is a key secondary filter. A lower Box % means you are 
          paying less for the sealed product relative to the cards inside — historically a better entry point 
          for long-term appreciation.
        </p>
        <div className="bg-slate-900 border border-amber-500/20 rounded-xl p-4 text-sm text-slate-400">
          <span className="text-amber-400 font-medium">Data note: </span>
          Rankings are based on 3 months of tracked price data (Feb–Apr 2026) and current eBay UK sold listing averages. 
          Scores are generated monthly by Groq AI. This is not financial advice.
        </div>
      </div>

      <h2 className="text-xl font-bold text-white mb-6">Top 10 Booster Boxes to Hold in 2026</h2>

      <div className="space-y-4">
        {sets.map(s => (
          <div key={s.slug} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-3">
                <span className="text-slate-500 font-bold text-lg w-6">#{s.rank}</span>
                <div>
                  <Link href={`/sets/${s.slug}`} className="text-white font-semibold hover:text-blue-400 transition-colors">
                    {s.name}
                  </Link>
                  <p className="text-slate-500 text-xs mt-0.5">{s.era} · £{s.price.toLocaleString()}</p>
                </div>
              </div>
              <RecBadge rec={s.rec} />
            </div>
            <ScoreDots score={s.score} />
            <p className="text-slate-500 text-xs mt-1 mb-3">{s.score}/20 · Box {s.boxPct}% of set value</p>
            <p className="text-slate-400 text-sm leading-relaxed">{s.highlight}</p>
            <Link href={`/sets/${s.slug}`} className="text-blue-400 text-xs mt-3 inline-block hover:text-blue-300">
              View price history & full score →
            </Link>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-3">Methodology</h3>
        <div className="space-y-2 text-sm text-slate-400">
          <p><strong className="text-slate-300">Scarcity (1–5):</strong> Based on print run status. Out-of-print scores higher, still-in-print scores lower.</p>
          <p><strong className="text-slate-300">Liquidity (1–5):</strong> How quickly sealed boxes sell on eBay UK. High velocity = high score.</p>
          <p><strong className="text-slate-300">Mascot Power (1–5):</strong> Collector demand for the primary chase Pokémon. Charizard, Eevee, Umbreon score highest.</p>
          <p><strong className="text-slate-300">Set Depth (1–5):</strong> Number of high-value cards across the set. More chase tiers = lower single-card dependency.</p>
          <p><strong className="text-slate-300">Box %:</strong> Booster box price ÷ total set value. Below 60% is generally considered good value.</p>
        </div>
      </div>
    </div>
  )
}
