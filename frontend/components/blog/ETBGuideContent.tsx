import Link from "next/link"

interface ETBRow {
  rank: number
  name: string
  slug: string
  promo: string
  price: number
  premium: number
  psaRatio: number | null
  setName: string
  highlight: string
}

const etbs: ETBRow[] = [
  { rank: 1, name: "PC 151 ETB", slug: "pc-151-etb", promo: "Snorlax", price: 1090.83, premium: 1883.7, psaRatio: null, setName: "151", highlight: "Highest sealed premium in the tracker at 1,884% above MSRP. Snorlax promo from one of the most beloved sets in the modern era. Long-term hold thesis remains strong." },
  { rank: 2, name: "PC Paldean Fates ETB", slug: "pc-paldean-fates-etb", promo: "Shiny Mimikyu", price: 519.81, premium: 845.3, psaRatio: null, setName: "Paldean Fates", highlight: "Shiny Mimikyu promo drives intense collector demand. Paldean Fates shiny vault makes this set a standout. 845% sealed premium with strong liquidity." },
  { rank: 3, name: "PC Prismatic Evolutions ETB", slug: "pc-prismatic-evolutions-etb", promo: "Eevee", price: 517.57, premium: 841.2, psaRatio: null, setName: "Prismatic Evolutions", highlight: "Eevee stamped promo from the most sought-after set of 2025. Prismatic Evolutions demand shows no sign of fading. One of the strongest near-term investment cases." },
  { rank: 4, name: "PC Obsidian Flames ETB", slug: "pc-obsidian-flames-etb", promo: "Moltres", price: 686.41, premium: 1148.3, psaRatio: null, setName: "Obsidian Flames", highlight: "1,148% premium is extraordinary. Moltres promo from a beloved SWSH-era set. High price point but exceptional collector appeal for the right buyer." },
  { rank: 5, name: "PC Crown Zenith ETB", slug: "pc-crown-zenith-etb", promo: "Lucario", price: 471.19, premium: 756.9, psaRatio: null, setName: "Crown Zenith", highlight: "Lucario promo from the final SWSH set. Crown Zenith Galarian Gallery cards maintain strong values. Established collector favourite with consistent demand." },
  { rank: 6, name: "PC Evolving Skies ETB", slug: "pc-evolving-skies-etb", promo: "Rayquaza", price: 834.78, premium: 1418.1, psaRatio: null, setName: "Evolving Skies", highlight: "Rayquaza stamped promo from arguably the most collectible SWSH set. 1,418% premium reflects the cult status of Evolving Skies in the collector community." },
  { rank: 7, name: "PC Destined Rivals ETB", slug: "pc-destined-rivals-etb", promo: "Team Rocket's Wobbuffet", price: 593.64, premium: 979.5, psaRatio: null, setName: "Destined Rivals", highlight: "Team Rocket nostalgia is powerful in 2026. Wobbuffet promo from a highly anticipated set — 980% premium on a product barely released shows serious speculative interest." },
  { rank: 8, name: "PC Fusion Strike ETB", slug: "pc-fusion-strike-etb", promo: "Mew", price: 445.24, premium: 709.7, psaRatio: null, setName: "Fusion Strike", highlight: "Mew promo — iconic mascot power. Fusion Strike is a deep set with Mew VMAX as the headline chase. Under £450 is a reasonable entry for the promo alone." },
  { rank: 9, name: "PC Paldea Evolved ETB", slug: "pc-paldea-evolved-etb", promo: "Tinkatink", price: 741.32, premium: 1248.1, psaRatio: null, setName: "Paldea Evolved", highlight: "1,248% premium for a less iconic promo suggests broader Paldea-era collector enthusiasm. Strong investment from a purely sealed-premium perspective." },
  { rank: 10, name: "PC Phantasmal Flames ETB", slug: "pc-phantasmal-flames-etb", promo: "Charcadet", price: 262.69, premium: 377.7, psaRatio: null, setName: "Phantasmal Flames", highlight: "Most accessible price point in the top 10 at £263. Charcadet promo with 378% premium — entry-level ETB investment for those starting out." },
]

export function ETBGuideContent() {
  return (
    <div>
      <div className="mb-8">
        <p className="text-slate-300 leading-relaxed mb-4">
          Pokemon Centre exclusive ETBs include a unique stamped promo card not available in standard retail products.
          This exclusivity drives significant secondary market premiums above the £54.99 MSRP. Rankings below are 
          ordered by sealed premium percentage — how much above retail price the sealed ETB is currently trading.
        </p>
        <p className="text-slate-300 leading-relaxed mb-4">
          A high sealed premium alone doesn&apos;t make something a good investment — the promo card desirability, 
          set collectibility, and overall liquidity all matter. Commentary below reflects all three factors.
        </p>
        <div className="grid grid-cols-2 gap-3 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-center">
            <p className="text-slate-400 text-xs mb-1">ETBs Tracked</p>
            <p className="text-white text-2xl font-bold">27</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-center">
            <p className="text-slate-400 text-xs mb-1">Avg Sealed Premium</p>
            <p className="text-white text-2xl font-bold">545%</p>
          </div>
        </div>
        <div className="bg-slate-900 border border-amber-500/20 rounded-xl p-4 text-sm text-slate-400">
          <span className="text-amber-400 font-medium">Data note: </span>
          Prices from eBay UK sold listings. PSA grading data is limited — ratio shown where available. 
          Weekly cron pipeline launching shortly will add historical price trend data. Not financial advice.
        </div>
      </div>

      <h2 className="text-xl font-bold text-white mb-6">Top 10 Pokemon Centre ETBs — Ranked by Sealed Premium</h2>

      <div className="space-y-4">
        {etbs.map(e => (
          <div key={e.slug} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex items-center gap-3">
                <span className="text-slate-500 font-bold text-lg w-6">#{e.rank}</span>
                <div>
                  <Link href={`/etbs/${e.slug}`} className="text-white font-semibold hover:text-blue-400 transition-colors">
                    {e.name.replace("Pokemon Centre ", "PC ")}
                  </Link>
                  <p className="text-slate-500 text-xs mt-0.5">{e.setName} · Promo: {e.promo}</p>
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="text-emerald-400 font-bold text-sm">+{e.premium.toFixed(0)}%</p>
                <p className="text-slate-500 text-xs">£{e.price.toLocaleString()}</p>
              </div>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed mt-3">{e.highlight}</p>
            <Link href={`/etbs/${e.slug}`} className="text-blue-400 text-xs mt-3 inline-block hover:text-blue-300">
              View full ETB data →
            </Link>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-3">What is Sealed Premium?</h3>
        <p className="text-slate-400 text-sm leading-relaxed">
          Sealed premium = (Current eBay UK sold price − MSRP £54.99) ÷ MSRP × 100. A 500% sealed premium 
          means the ETB is selling for 5× its retail price on the secondary market. The higher the premium, 
          the more the market values the sealed product over opening it — a signal of collector confidence in 
          the long-term value of both the box and the promo card inside.
        </p>
        <p className="text-slate-400 text-sm leading-relaxed mt-3">
          PSA Premium Ratio (where available) = PSA 10 graded promo price ÷ Raw promo price. A ratio above 3× 
          suggests strong grading upside — opening and grading the promo card may be more profitable than holding sealed.
        </p>
      </div>
    </div>
  )
}
