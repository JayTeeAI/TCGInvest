import { getETBs, getETBHistory } from "@/lib/api"
import { getUser } from "@/lib/auth"
import { Disclaimer } from "@/components/Disclaimer"
import { ETBPageClient } from "@/components/etbs/ETBPageClient"
import SetAlertButton from "@/components/alerts/SetAlertButton"
import Link from "next/link"
import { notFound } from "next/navigation"
import type { Metadata } from "next"

export const revalidate = 3600

function toSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/pokemon centre /g, "pc-")
    .replace(/s&v/gi, "sandv")
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
}

function formatGBP(value: number | null): string {
  if (value == null) return "—"
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", minimumFractionDigits: 2 }).format(value)
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params
  const etbs = await getETBs().catch(() => [])
  const list = Array.isArray(etbs) ? etbs : (etbs as any).etbs ?? []
  const etb = list.find((e: any) => toSlug(e.name) === slug)
  if (!etb) return { title: "ETB Not Found | TCG Invest" }
  const price = etb.ebay_avg_sold_gbp ? formatGBP(etb.ebay_avg_sold_gbp) : "tracked"
  const premium = etb.sealed_premium_pct ? `${etb.sealed_premium_pct.toFixed(0)}%` : null
  return {
    title: `${etb.name} Price & Investment Analysis 2026`,
    description: `${etb.name} current sealed price is ${price}${premium ? `, ${premium} above MSRP` : ""}. Track promo card value, PSA 10 premium ratio and price history. Updated weekly.`,
    keywords: [
      `${etb.name.toLowerCase()} price`,
      `${etb.name.toLowerCase()} sealed price uk`,
      `${etb.set_name?.toLowerCase()} pokemon centre etb`,
      `${etb.set_name?.toLowerCase()} etb investment`,
      "pokemon centre etb tracker",
      "pokemon etb sealed price uk",
    ],
    alternates: { canonical: `https://tcginvest.uk/etbs/${slug}` },
    openGraph: {
      title: `${etb.name} Price & Investment Analysis 2026`,
      description: `Sealed price ${price}${premium ? ` · ${premium} above MSRP` : ""} · Weekly eBay UK data`,
      url: `https://tcginvest.uk/etbs/${slug}`,
      images: [{ url: "/og-etb.png", width: 1200, height: 630, alt: `${etb.name} Price Tracker` }],
    },
    twitter: {
      card: "summary_large_image",
      title: `${etb.name} Price Tracker`,
      description: `Sealed price ${price}${premium ? ` · ${premium} above MSRP` : ""} · Weekly eBay UK data`,
      images: ["/og-etb.png"],
    },
  }
}

export default async function ETBPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const [etbsData, userData] = await Promise.allSettled([getETBs(), getUser()])
  const rawEtbs = etbsData.status === "fulfilled" ? etbsData.value : []
  const etbs = Array.isArray(rawEtbs) ? rawEtbs : (rawEtbs as any).etbs ?? []
  const user = userData.status === "fulfilled" && userData.value.authenticated ? userData.value : null
  const etb = etbs.find((e: any) => toSlug(e.name) === slug)
  if (!etb) notFound()
  const historyData = await getETBHistory(etb.id).catch(() => ({ history: [] }))
  const history = historyData.history || []
  const sealedPremiumPct = etb.sealed_premium_pct ?? 0
  const premiumColor = sealedPremiumPct > 300
    ? "text-red-400" : sealedPremiumPct > 100
    ? "text-orange-400" : "text-green-400"

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: etb.name,
    description: `Pokemon Centre exclusive Elite Trainer Box. Sealed price ${formatGBP(etb.ebay_avg_sold_gbp)}, ${etb.sealed_premium_pct?.toFixed(0)}% above MSRP of £${etb.msrp_gbp}.`,
    brand: { "@type": "Brand", name: "Pokémon TCG" },
    offers: etb.ebay_avg_sold_gbp ? {
      "@type": "Offer",
      price: etb.ebay_avg_sold_gbp.toFixed(2),
      priceCurrency: "GBP",
      availability: "https://schema.org/InStock",
      seller: { "@type": "Organization", name: "TCG Invest" },
    } : undefined,
  }

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <main className="min-h-screen bg-slate-950 text-slate-100">
        <div className="max-w-4xl mx-auto px-6 py-12">

          <div className="flex items-center gap-2 text-sm text-slate-500 mb-8">
            <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
            <span>&rsaquo;</span>
            <Link href="/tools/etb-tracker" className="hover:text-slate-300 transition-colors">ETB Tracker</Link>
            <span>&rsaquo;</span>
            <span className="text-slate-300">{etb.name}</span>
          </div>

          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">{etb.name}</h1>
            <div className="flex flex-wrap items-center gap-2 text-slate-400 text-sm">
              <span>{etb.set_name}</span>
              <span>&middot;</span>
              <span>Released {etb.available_date?.slice(0, 7)}</span>
              {etb.is_stamped_promo && (
                <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-full">Stamped Promo</span>
              )}
              <span className="text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full">{etb.pack_count} packs</span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">Sealed Price</p>
              <p className="text-white text-2xl font-bold">{formatGBP(etb.ebay_avg_sold_gbp)}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">MSRP</p>
              <p className="text-white text-2xl font-bold">{formatGBP(etb.msrp_gbp)}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">Sealed Premium</p>
              <p className={`text-2xl font-bold ${premiumColor}`}>
                {etb.sealed_premium_pct != null ? `${etb.sealed_premium_pct.toFixed(0)}%` : "—"}
              </p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-1">PSA Premium Ratio</p>
              <p className="text-white text-2xl font-bold">
                {etb.psa_premium_ratio != null ? `${etb.psa_premium_ratio.toFixed(2)}x` : "—"}
              </p>
            </div>
          </div>

          {etb.ebay_avg_sold_gbp && (
            <SetAlertButton
              productType="etb"
              productId={etb.id}
              productName={etb.name}
              currentPrice={etb.ebay_avg_sold_gbp}
            />
          )}

          <div className="mt-6"><Disclaimer /></div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6 mt-6">
            <h2 className="text-slate-200 font-semibold mb-4">Promo Card &mdash; {etb.promo_pokemon}</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-slate-400 text-xs mb-1">Raw Promo Price</p>
                <p className="text-white text-xl font-bold">{formatGBP(etb.raw_promo_gbp)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs mb-1">PSA 10 Price</p>
                <p className="text-white text-xl font-bold">{formatGBP(etb.psa10_promo_gbp)}</p>
              </div>
            </div>
            {etb.psa_premium_ratio != null && (
              <p className="text-slate-500 text-xs mt-3">
                Grading adds {((etb.psa_premium_ratio - 1) * 100).toFixed(0)}% value over raw &mdash;{" "}
                {etb.psa_premium_ratio >= 3
                  ? "strong grading case"
                  : etb.psa_premium_ratio >= 2
                  ? "moderate grading upside"
                  : "limited grading premium"}
              </p>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
            <h2 className="text-slate-200 font-semibold mb-4">Price History</h2>
            {user ? (
              <ETBPageClient history={history} etbName={etb.name} />
            ) : (
              <div className="text-center py-8">
                <p className="text-slate-400 text-sm mb-3">Sign in free to view price history charts</p>
                <a href="/auth/google" className="bg-white text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors">
                  Sign in free &rarr;
                </a>
              </div>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-700 rounded-xl px-5 py-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-slate-200 text-sm font-medium">Compare all 27 PC ETBs</p>
              <p className="text-slate-500 text-xs mt-0.5">See where {etb.set_name} ranks across the full ETB tracker</p>
            </div>
            <Link href="/tools/etb-tracker" className="bg-white text-slate-900 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors whitespace-nowrap">
              View full tracker &rarr;
            </Link>
          </div>

          <p className="text-slate-600 text-xs mt-8">
            Sealed Premium = (Current price &minus; MSRP) &divide; MSRP &times; 100. PSA Premium Ratio = PSA 10 promo price &divide; Raw promo price. Prices sourced from eBay UK sold listings. Updated weekly. TCG Invest is not affiliated with The Pok&eacute;mon Company International.
          </p>

        </div>
      </main>
    </>
  )
}
