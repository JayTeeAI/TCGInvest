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
        <p className="text-slate-500 text-xs">£{prev.toLocaleString()} → £{curr.toLocaleString()}</p>
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
        <p className="text-slate-500 text-xs">£{prev.toLocaleString()} → £{curr.toLocaleString()}</p>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h2 className="text-xl font-bold text-white mb-4">{title}</h2>
      {children}
    </div>
  )
}

export function MoverPostContent() {
  return (
    <div className="prose-custom">

      <Section title="Overview">
        <p className="text-slate-300 leading-relaxed mb-4">
          April 2026 saw some of the most dramatic price movements in recent memory for Pokemon TCG sealed products.
          Prismatic Evolutions continued its extraordinary run, surging 235% month-on-month as demand for the Eevee promo
          shows no signs of slowing. Meanwhile, older Sun &amp; Moon era sets pulled back sharply as collectors rotated
          into newer products.
        </p>
        <p className="text-slate-300 leading-relaxed">
          Data covers 43 tracked booster box sets, comparing March 2026 to April 2026 eBay UK sold listing averages.
        </p>
      </Section>

      <Section title="🚀 Biggest Gainers — April 2026">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <GainRow name="Prismatic Evolutions" slug="prismatic-evolutions" prev={280} curr={938.60} pct={235.2} rec="Accumulate" />
          <GainRow name="151" slug="151" prev={780} curr={2214.14} pct={183.9} rec="Overvalued" />
          <GainRow name="Paldean Fates" slug="paldean-fates" prev={800} curr={1470.72} pct={83.8} rec="Accumulate" />
          <GainRow name="Ascended Heroes" slug="ascended-hereos" prev={280} curr={451.22} pct={61.2} rec="Accumulate" />
          <GainRow name="Silver Tempest" slug="silver-tempest" prev={260} curr={413.65} pct={59.1} rec="Strong Buy" />
        </div>
        <p className="text-slate-500 text-xs mt-3">
          Prismatic Evolutions and 151 both carry &quot;Overvalued&quot; or &quot;Accumulate&quot; ratings despite strong price action — 
          the AI scoring model flags that box price now significantly exceeds set value, making new entry at current prices risky.
        </p>
      </Section>

      <Section title="📉 Biggest Drops — April 2026">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <DropRow name="Lost Thunder" slug="lost-thunder" prev={1757} curr={1372.18} pct={-21.9} rec="Hold" />
          <DropRow name="Ultra Prism" slug="ultra-prism" prev={1671} curr={1331.18} pct={-20.3} rec="Hold" />
          <DropRow name="S&V Base Set" slug="sandv-base-set" prev={255} curr={225.62} pct={-11.5} rec="Accumulate" />
          <DropRow name="Mega Evolution (Enhanced)" slug="mega-evolution-enhanced" prev={270} curr={240.67} pct={-10.9} rec="Strong Buy" />
          <DropRow name="Sword and Shield" slug="sword-and-shield" prev={665} curr={592.64} pct={-10.9} rec="Overvalued" />
        </div>
        <p className="text-slate-500 text-xs mt-3">
          The drops in Lost Thunder and Ultra Prism are notable — both remain &quot;Hold&quot; rated, suggesting the AI model
          sees these as fairly valued at lower prices. Mega Evolution (Enhanced) dropping to &quot;Strong Buy&quot; territory 
          with a box % of just 23.6% may represent a genuine buying opportunity.
        </p>
      </Section>

      <Section title="What to Watch in May 2026">
        <div className="space-y-3">
          {[
            { set: "Silver Tempest", slug: "silver-tempest", note: "Strong Buy rating with 59% monthly gain — watch for consolidation or continuation above £400." },
            { set: "Mega Evolution (Enhanced)", slug: "mega-evolution-enhanced", note: "Strong Buy at £240 with box % of 23.6% — cards worth nearly 4x the box price. Data point to watch." },
            { set: "Brilliant Stars", slug: "brilliant-stars", note: "20/20 AI score and Strong Buy — currently the highest-rated set in the tracker. Any dip below £500 has historically been short-lived." },
          ].map(({ set, slug, note }) => (
            <div key={slug} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <Link href={`/sets/${slug}`} className="text-white font-medium text-sm hover:text-blue-400 transition-colors">{set}</Link>
              <p className="text-slate-400 text-sm mt-1">{note}</p>
            </div>
          ))}
        </div>
      </Section>

      <p className="text-slate-500 text-xs mt-6">
        Price data sourced from eBay UK sold listings. Comparison period: March 2026 vs April 2026. 
        AI investment scores generated using Groq llama-3.3-70b across four dimensions: Scarcity, Liquidity, Mascot Power, Set Depth.
        Next update: May 2026 pipeline run.
      </p>

    </div>
  )
}
