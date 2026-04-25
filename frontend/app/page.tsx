import { getTools, getSummary } from "@/lib/api"
import { getUser } from "@/lib/auth"
import { fetchPosts, type BlogPost } from "@/lib/blog/posts"
import Link from "next/link"
import type { Metadata } from "next"

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: "Pokémon TCG Investment Tools — Booster Box, ETB & Chase Card Tracker",
  description:
    "Free Pokémon TCG investment tools. Track booster box prices, AI investment scores, Elite Trainer Box values, and chase card grading ROI across 44+ sets. Updated weekly.",
  alternates: {
    canonical: "https://tcginvest.uk",
  },
  openGraph: {
    title: "Pokémon TCG Investment Tools — Booster Box, ETB & Chase Card Tracker",
    description:
      "Free Pokémon TCG investment tools. Track booster box prices, AI investment scores, Elite Trainer Box values, and chase card grading ROI across 44+ sets.",
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
    "Pokémon TCG investment platform providing weekly price tracking and AI-powered investment scores.",
  knowsAbout: [
    "Pokémon TCG investing",
    "Sealed product investment",
    "Booster box price tracking",
    "Elite Trainer Box analysis",
    "Chase card grading ROI",
  ],
}

export default async function HomePage() {
  const [toolsData, summaryData, postsData, moversData, userData] = await Promise.allSettled([
    getTools(),
    getSummary(),
    fetchPosts(3),
    fetch("http://127.0.0.1:8000/api/movers/daily", { next: { revalidate: 3600 } })
      .then(r => r.ok ? r.json() : null)
      .catch(() => null),
    getUser(),
  ])

  const tools = toolsData.status === "fulfilled" ? toolsData.value.tools : []
  const summary = summaryData.status === "fulfilled" ? summaryData.value : null
  const latestPosts = postsData.status === "fulfilled" ? postsData.value : []
  const movers = moversData.status === "fulfilled" ? moversData.value : null
  const user = userData.status === "fulfilled" && userData.value?.authenticated ? userData.value : null
  const isPremiumUser = user?.role === "premium" || user?.role === "admin"

  const stats = summary?.stats ?? null

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
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">

          {/* ── Hero ───────────────────────────────────────────── */}
          <div className="mb-6">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-3">
              TCG Invest
            </h1>
            <p className="text-slate-400 text-base sm:text-lg max-w-xl">
              Pokémon TCG investment tools for serious collectors and investors.
            </p>
          </div>

          {/* ── Stats row ──────────────────────────────────────── */}
          {stats && (
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 text-center">
                <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">Sets</p>
                <p className="text-2xl font-bold text-white">{stats.total_sets}</p>
                <p className="text-slate-600 text-xs mt-1 hidden sm:block">tracked</p>
              </div>
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 text-center">
                <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">ETBs</p>
                <p className="text-2xl font-bold text-white">{stats.etb_count ?? 27}</p>
                <p className="text-slate-600 text-xs mt-1 hidden sm:block">tracked</p>
              </div>
              <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 text-center">
                <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">Chase Cards</p>
                <p className="text-2xl font-bold text-yellow-400">{stats.chase_cards_count ?? 79}</p>
                <p className="text-slate-600 text-xs mt-1 hidden sm:block">tracked</p>
              </div>
            </div>
          )}

          {/* ── Daily Movers ───────────────────────────────────── */}
          {movers && (movers.risers?.length > 0 || movers.fallers?.length > 0) && (
            <DailyMoversStrip movers={movers} isPremium={isPremiumUser} />
          )}

          {/* ── Tools ──────────────────────────────────────────── */}
          <h2 className="text-lg font-semibold text-slate-300 mb-4">Tools</h2>
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {tools.map((tool: any) => (
              <ToolCard key={tool.slug} tool={tool} />
            ))}
          </div>

          {/* ── Blog ───────────────────────────────────────────── */}
          {latestPosts.length > 0 && (
            <div className="mt-0">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-300">Latest from the Blog</h2>
                <Link href="/blog" className="text-blue-400 hover:text-blue-300 text-sm transition-colors">
                  View all →
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {latestPosts.map((post: BlogPost) => (
                  <BlogCard key={post.slug} post={post} />
                ))}
              </div>
            </div>
          )}

          <p className="text-slate-700 text-xs mt-8 text-center">
            Data updated monthly · Prices in GBP · Not financial advice · TCG Invest is not affiliated with The Pokémon Company International
          </p>
        </div>
      </main>
    </>
  )
}


// ── Daily Movers Strip ─────────────────────────────────────────────────────
function MoverPill({ item, isRiser }: { item: any; isRiser: boolean }) {
  const sign  = isRiser ? "+" : ""
  const color = isRiser
    ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
    : "text-red-400 bg-red-500/10 border-red-500/20"
  const arrow = isRiser ? "▲" : "▼"
  return (
    <a
      href={`/sets/${item.slug}`}
      className="flex items-center gap-2.5 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 hover:border-slate-600 transition-colors min-w-0"
    >
      {item.logo_url && (
        <img
          src={item.logo_url}
          alt={item.set_name}
          className="h-6 w-auto object-contain shrink-0"
          loading="lazy"
        />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-white text-xs font-semibold truncate leading-tight">{item.set_name}</p>
        <p className="text-slate-500 text-xs">£{item.price_gbp.toFixed(2)}</p>
      </div>
      <span className={`text-xs font-bold px-1.5 py-0.5 rounded border ${color} shrink-0`}>
        {arrow} {sign}{item.change_pct_24h.toFixed(2)}%
      </span>
    </a>
  )
}

function DailyMoversStrip({ movers, isPremium = false }: { movers: any; isPremium?: boolean }) {
  const risers: any[]  = movers.risers  ?? []
  const fallers: any[] = movers.fallers ?? []
  // Free: show top 3 risers only. We can't gate this per-user server-side on homepage
  // without auth — so show top 3 visibly, blur the rest as a premium teaser.
  const visibleRisers  = isPremium ? risers : risers.slice(0, 3)
  const lockedRisers   = isPremium ? [] : risers.slice(3)
  const asOf = movers.as_of
    ? new Date(movers.as_of).toLocaleDateString("en-GB", { day: "numeric", month: "short" })
    : ""

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">📈</span>
          <h2 className="text-sm font-semibold text-slate-300">Today&apos;s Movers</h2>
          {asOf && <span className="text-slate-600 text-xs">{asOf}</span>}
        </div>
        <a href="/tools/tracker" className="text-blue-400 hover:text-blue-300 text-xs transition-colors">
          Full tracker →
        </a>
      </div>

      {/* Risers */}
      <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">Top Risers</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
        {visibleRisers.map((item: any) => (
          <MoverPill key={item.slug} item={item} isRiser={true} />
        ))}
        {lockedRisers.map((item: any) => (
          <div key={item.slug} className="relative">
            <div className="pointer-events-none select-none blur-sm opacity-50">
              <MoverPill item={item} isRiser={true} />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <a
                href="/premium"
                className="text-xs text-yellow-400 font-semibold bg-slate-950/80 px-2 py-0.5 rounded"
              >
                🔒 Premium
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Fallers — premium sees all unblurred; free/unauthed sees gated teaser */}
      <div className="relative">
        <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">Top Fallers</p>
        {isPremium ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {fallers.slice(0, 3).map((item: any) => (
              <MoverPill key={item.slug} item={item} isRiser={false} />
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pointer-events-none select-none blur-sm opacity-40">
              {fallers.slice(0, 3).map((item: any) => (
                <MoverPill key={item.slug} item={item} isRiser={false} />
              ))}
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <a
                href="/premium"
                className="text-sm text-yellow-400 font-bold bg-slate-950/90 border border-yellow-500/30 px-4 py-1.5 rounded-lg hover:border-yellow-400/60 transition-colors"
              >
                🔒 Unlock fallers — Premium
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function ToolCard({ tool }: { tool: any }) {
  const isLive = tool.status === "live"

  const TOOL_ICONS: Record<string, string> = {
    "tracker": "📦",
    "etb-tracker": "🎁",
    "chase-cards": "✨",
    "roi-calculator": "📊",
    "price-alerts": "🔔",
    "portfolio": "💼",
  }

  const icon = TOOL_ICONS[tool.slug] ?? "🔧"

  const card = (
    <div className={`
      h-full rounded-xl border p-5 transition-all duration-200 flex flex-col
      ${isLive
        ? "bg-slate-900 border-slate-800 hover:border-slate-600 hover:bg-slate-800/80 cursor-pointer"
        : "bg-slate-900/50 border-slate-800/50 opacity-60"
      }
    `}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">{icon}</span>
          <h3 className="text-white font-semibold text-base leading-tight">{tool.name}</h3>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 border ${
          isLive
            ? "bg-green-900/50 text-green-300 border-green-800"
            : "bg-slate-800 text-slate-500 border-slate-700"
        }`}>
          {isLive ? "Live" : "Soon"}
        </span>
      </div>
      <p className="text-slate-400 text-sm leading-relaxed flex-1">{tool.description}</p>
      {tool.updated && (
        <p className="text-slate-600 text-xs mt-3">Updated {tool.updated}</p>
      )}
    </div>
  )

  return isLive ? (
    <Link href={tool.route} className="block h-full">{card}</Link>
  ) : (
    <div className="h-full">{card}</div>
  )
}

const CATEGORY_COLORS: Record<string, string> = {
  movers: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  guide: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  analysis: "bg-purple-500/10 text-purple-400 border border-purple-500/20",
}

const CATEGORY_LABELS: Record<string, string> = {
  movers: "Price Movers",
  guide: "Investment Guide",
  analysis: "Analysis",
}

function BlogCard({ post }: { post: BlogPost }) {
  function formatDate(d: string) {
    return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
  }
  return (
    <Link
      href={`/blog/${post.slug}`}
      className="block bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-600 transition-colors group"
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[post.category]}`}>
          {CATEGORY_LABELS[post.category]}
        </span>
        <span className="text-slate-600 text-xs shrink-0">{post.readTime} min</span>
      </div>
      <h3 className="text-white font-semibold text-sm leading-snug mb-2 group-hover:text-blue-400 transition-colors line-clamp-2">
        {post.title}
      </h3>
      <p className="text-slate-500 text-xs leading-relaxed line-clamp-2">{post.description}</p>
      <p className="text-slate-600 text-xs mt-3">{formatDate(post.date)}</p>
    </Link>
  )
}
