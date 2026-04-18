import { getTools, getSummary } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import type { Metadata } from "next"

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: "Pokémon TCG Investment Tools — Booster Box & ETB Price Tracker",
  description:
    "Free Pokémon TCG investment tools. Track booster box prices, AI investment scores, and Elite Trainer Box values across 44+ sets. Updated monthly.",
  alternates: {
    canonical: "https://tcginvest.uk",
  },
  openGraph: {
    title: "Pokémon TCG Investment Tools — Booster Box & ETB Price Tracker",
    description:
      "Free Pokémon TCG investment tools. Track booster box prices, AI investment scores, and Elite Trainer Box values across 44+ sets.",
    url: "https://tcginvest.uk",
  },
}

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "TCG Invest",
  url: "https://tcginvest.uk",
  description:
    "Data-driven Pokémon TCG investment tools for serious collectors and investors.",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://tcginvest.uk/tools/tracker?set={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
}

const organisationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "TCG Invest",
  url: "https://tcginvest.uk",
  description:
    "Pokémon TCG investment platform providing monthly price tracking and AI-powered investment scores.",
  knowsAbout: [
    "Pokémon TCG investing",
    "Sealed product investment",
    "Booster box price tracking",
    "Elite Trainer Box analysis",
  ],
}

export default async function HomePage() {
  const [toolsData, summaryData] = await Promise.allSettled([
    getTools(),
    getSummary(),
  ])

  const tools = toolsData.status === "fulfilled" ? toolsData.value.tools : []
  const summary = summaryData.status === "fulfilled" ? summaryData.value : null

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organisationJsonLd) }}
      />
      <main className="min-h-screen bg-slate-950 text-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-16">

          <div className="mb-12">
            <h1 className="text-4xl font-bold tracking-tight text-white mb-3">
              TCG Invest
            </h1>
            <p className="text-slate-400 text-lg">
              Pokémon TCG investment tools for serious collectors and investors.
            </p>
          </div>

          {summary?.stats && (
            <div className="grid grid-cols-2 gap-4 mb-12 max-w-sm">
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
                <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Sets tracked</p>
                <p className="text-2xl font-bold text-white">{summary.stats.total_sets}</p>
              </div>
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
                <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">ETBs tracked</p>
                <p className="text-2xl font-bold text-white">{summary.stats.etb_count ?? 27}</p>
              </div>
            </div>
          )}

          <h2 className="text-xl font-semibold text-slate-300 mb-6">Tools</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tools.map((tool: any) => (
              <ToolCard key={tool.slug} tool={tool} />
            ))}
          </div>

          <p className="text-slate-600 text-sm mt-16 text-center">
            Data updated monthly · Prices in GBP · Not financial advice · TCG Invest is not affiliated with The Pokémon Company International
          </p>
        </div>
      </main>
    </>
  )
}

function ToolCard({ tool }: { tool: any }) {
  const isLive = tool.status === "live"

  const card = (
    <Card className={`
      bg-slate-900 border-slate-800 h-full transition-all duration-200
      ${isLive ? "hover:border-slate-600 hover:bg-slate-800 cursor-pointer" : "opacity-60"}
    `}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-white text-lg">{tool.name}</CardTitle>
          <Badge className={isLive
            ? "bg-green-900 text-green-300 border-green-800 shrink-0"
            : "bg-slate-800 text-slate-500 border-slate-700 shrink-0"
          }>
            {isLive ? "Live" : "Coming soon"}
          </Badge>
        </div>
        <CardDescription className="text-slate-400">
          {tool.description}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {tool.updated && (
          <p className="text-slate-500 text-xs">Updated {tool.updated}</p>
        )}
      </CardContent>
    </Card>
  )

  return isLive ? (
    <Link href={tool.route} className="block h-full">{card}</Link>
  ) : (
    <div className="h-full">{card}</div>
  )
}
