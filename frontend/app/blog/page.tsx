import Link from "next/link"
import { fetchPosts } from "@/lib/blog/posts"
import type { Metadata } from "next"

export const revalidate = 3600

export const metadata: Metadata = {
  title: "Pokemon TCG Investment Blog — Price Movers, Analysis & Guides",
  description: "Weekly Pokemon TCG sealed product price movements, booster box investment analysis and collector guides. Data-driven insights updated regularly.",
  keywords: [
    "pokemon tcg investment blog",
    "pokemon booster box price movers",
    "pokemon sealed investment guide",
    "pokemon tcg market analysis 2026",
  ],
  alternates: { canonical: "https://tcginvest.uk/blog" },
  openGraph: {
    title: "Pokemon TCG Investment Blog",
    description: "Weekly price movers, booster box rankings and investment analysis for Pokemon TCG sealed products.",
    url: "https://tcginvest.uk/blog",
    images: [{ url: "/og-default.png", width: 1200, height: 630 }],
  },
}

const CATEGORY_LABELS: Record<string, string> = {
  movers: "Price Movers",
  guide: "Investment Guide",
  analysis: "Analysis",
}

const CATEGORY_COLORS: Record<string, string> = {
  movers: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  guide: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  analysis: "bg-purple-500/10 text-purple-400 border border-purple-500/20",
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })
}

export default async function BlogIndex() {
  const posts = await fetchPosts(50)

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-4xl mx-auto px-6 py-12">

        <div className="mb-10">
          <Link href="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors mb-4 inline-block">← Home</Link>
          <h1 className="text-3xl font-bold text-white mb-3">TCG Invest Blog</h1>
          <p className="text-slate-400">Price movers, investment analysis and guides for Pokemon TCG sealed products. Updated weekly.</p>
        </div>

        {posts.length === 0 ? (
          <p className="text-slate-500 text-sm">No posts yet — check back soon.</p>
        ) : (
          <div className="space-y-4">
            {posts.map(post => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="block bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-600 transition-colors group"
              >
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[post.category]}`}>
                    {CATEGORY_LABELS[post.category]}
                  </span>
                  <span className="text-slate-500 text-xs">{formatDate(post.date)} · {post.readTime} min read</span>
                </div>
                <h2 className="text-white font-semibold text-lg mb-2 group-hover:text-blue-400 transition-colors">
                  {post.title}
                </h2>
                <p className="text-slate-400 text-sm leading-relaxed">{post.description}</p>
                <p className="text-blue-400 text-sm mt-3 font-medium">Read more →</p>
              </Link>
            ))}
          </div>
        )}

      </div>
    </main>
  )
}
