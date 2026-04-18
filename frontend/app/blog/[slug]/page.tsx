import { notFound } from "next/navigation"
import Link from "next/link"
import { getPost } from "@/lib/blog/posts"
import { MoverPostContent } from "@/components/blog/MoverPostContent"
import { BBGuideContent } from "@/components/blog/BBGuideContent"
import { ETBGuideContent } from "@/components/blog/ETBGuideContent"
import type { Metadata } from "next"

export const revalidate = 3600

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

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params
  const post = getPost(slug)
  if (!post) return { title: "Post Not Found | TCG Invest" }

  return {
    title: post.title,
    description: post.description,
    alternates: { canonical: `https://tcginvest.uk/blog/${slug}` },
    openGraph: {
      title: post.title,
      description: post.description,
      url: `https://tcginvest.uk/blog/${slug}`,
      images: [{ url: "/og-default.png", width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.description,
      images: ["/og-default.png"],
    },
  }
}

export default async function BlogPost({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const post = getPost(slug)
  if (!post) notFound()

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-6 py-12">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-8">
          <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
          <span>›</span>
          <Link href="/blog" className="hover:text-slate-300 transition-colors">Blog</Link>
          <span>›</span>
          <span className="text-slate-300 truncate">{post.title}</span>
        </div>

        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[post.category]}`}>
              {CATEGORY_LABELS[post.category]}
            </span>
            <span className="text-slate-500 text-sm">{formatDate(post.date)} · {post.readTime} min read</span>
          </div>
          <h1 className="text-3xl font-bold text-white leading-tight">{post.title}</h1>
          <p className="text-slate-400 mt-3 text-lg leading-relaxed">{post.description}</p>
        </div>

        {/* Disclaimer */}
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 mb-8">
          <div className="flex gap-3">
            <span className="text-amber-400 text-lg shrink-0">⚠</span>
            <p className="text-slate-500 text-xs leading-relaxed">
              For informational purposes only. Data sourced from eBay UK sold listings and TCG Invest\'s monthly price pipeline. Not financial advice.
            </p>
          </div>
        </div>

        {/* Content — routed by slug */}
        {slug === "pokemon-booster-box-movers-april-2026" && <MoverPostContent />}
        {slug === "best-booster-boxes-to-hold-2026" && <BBGuideContent />}
        {slug === "best-pokemon-centre-etbs-to-hold-2026" && <ETBGuideContent />}

        {/* CTA */}
        <div className="mt-12 bg-slate-900 border border-slate-700 rounded-xl px-5 py-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-slate-200 text-sm font-medium">Track these prices live</p>
            <p className="text-slate-500 text-xs mt-0.5">Free tools updated monthly — no account required for basic data</p>
          </div>
          <div className="flex gap-2">
            <Link href="/tools/tracker" className="bg-white text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors whitespace-nowrap">
              Booster Box Tracker →
            </Link>
            <Link href="/tools/etb-tracker" className="bg-slate-700 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors whitespace-nowrap">
              ETB Tracker →
            </Link>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-800">
          <Link href="/blog" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
            ← Back to blog
          </Link>
        </div>

      </div>
    </main>
  )
}
