export function formatGBP(value: number | null | undefined): string {
  if (value == null) return "—"
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    minimumFractionDigits: 2,
  }).format(value)
}

export function formatPct(value: number | null | undefined): string {
  if (value == null) return "—"
  // Values > 1 are already ratios stored as e.g. 1.284 = 128.4%
  // Values <= 1 are ratios stored as e.g. 0.247 = 24.7%
  const pct = value > 1 ? value * 100 : value * 100
  return `${pct.toFixed(1)}%`
}

export function formatRatio(value: number | null | undefined): string {
  if (value == null) return "—"
  return value.toFixed(2)
}

export function boxPctColor(value: number | null | undefined): string {
  if (value == null) return "bg-slate-700 text-slate-300"
  // value is a ratio: 0.5 = 50%, 1.0 = 100%, 1.5 = 150%
  if (value > 1.0)  return "bg-red-900 text-red-300"
  if (value >= 0.75) return "bg-orange-900 text-orange-300"
  if (value >= 0.5)  return "bg-yellow-900 text-yellow-300"
  return "bg-green-900 text-green-300"
}

export function scoreColor(value: number | null | undefined): string {
  if (value == null) return "bg-slate-700 text-slate-300"
  if (value >= 16) return "bg-green-900 text-green-300"
  if (value >= 12) return "bg-blue-900 text-blue-300"
  if (value >= 8)  return "bg-yellow-900 text-yellow-300"
  if (value >= 4)  return "bg-orange-900 text-orange-300"
  return "bg-red-900 text-red-300"
}

export function recColor(value: string | null | undefined): string {
  switch (value) {
    case "Strong Buy":  return "bg-green-600 text-white"
    case "Buy":         return "bg-green-900 text-green-300"
    case "Accumulate":  return "bg-blue-900 text-blue-300"
    case "Hold":        return "bg-slate-700 text-slate-300"
    case "Reduce":      return "bg-orange-900 text-orange-300"
    case "Sell":        return "bg-red-900 text-red-300"
    case "Overvalued":  return "bg-red-700 text-white"
    default:            return "bg-slate-700 text-slate-400"
  }
}

// ── Rule-based reasoning generator ───────────────────────────────────────────
interface SetData {
  bb_price_gbp:  number | null
  set_value_gbp: number | null
  box_pct:       number | null
  chase_pct:     number | null
  scarcity:      number | null
  liquidity:     number | null
  mascot_power:  number | null
  set_depth:     number | null
  decision_score: number | null
  recommendation: string | null
  print_status:  string | null
  top3_chase:    string | null
}

export function generateReasoning(s: SetData): string[] {
  const reasons: string[] = []

  // Box % analysis
  if (s.box_pct != null) {
    const pct = s.box_pct * 100
    if (pct > 150)
      reasons.push(`Box price is ${pct.toFixed(0)}% of set value — significantly overpriced vs card values`)
    else if (pct > 100)
      reasons.push(`Box price (${pct.toFixed(0)}% of set value) exceeds total card value — poor entry point`)
    else if (pct > 75)
      reasons.push(`Box price is ${pct.toFixed(0)}% of set value — limited upside at current price`)
    else if (pct > 50)
      reasons.push(`Box price is ${pct.toFixed(0)}% of set value — moderate value, some upside potential`)
    else
      reasons.push(`Box price is only ${pct.toFixed(0)}% of set value — strong value relative to card prices`)
  }

  // Chase card concentration
  if (s.chase_pct != null) {
    const pct = s.chase_pct * 100
    if (pct > 60)
      reasons.push(`Top 3 cards represent ${pct.toFixed(0)}% of set value — high concentration risk, value depends on pulling key cards`)
    else if (pct > 40)
      reasons.push(`Top 3 cards represent ${pct.toFixed(0)}% of set value — moderate concentration, reasonable spread`)
    else
      reasons.push(`Value spread across many cards (top 3 = ${pct.toFixed(0)}% of set value) — lower single-card dependency`)
  }

  // Scarcity
  if (s.scarcity != null) {
    if (s.scarcity >= 5)
      reasons.push("Recently went out of print — scarcity premium still forming, buy window may be open")
    else if (s.scarcity === 4)
      reasons.push("Out of print 2–4 years — established scarcity premium with some upside remaining")
    else if (s.scarcity === 3)
      reasons.push("Out of print 4+ years — fully priced in by market, scarcity opportunity has passed")
    else if (s.scarcity === 2)
      reasons.push("Approaching end of print run — watch for OOP announcement as a future entry signal")
    else
      reasons.push("Still in print — no scarcity premium, price unlikely to appreciate near term")
  }

  // Mascot power
  if (s.mascot_power != null) {
    if (s.mascot_power >= 5)
      reasons.push("Charizard, Eevee or Umbreon as primary chase — strong long-term collector demand")
    else if (s.mascot_power >= 4)
      reasons.push("Strong mascot presence as secondary chase — solid collector appeal")
    else if (s.mascot_power <= 2)
      reasons.push("Weak mascot presence — limited collector demand may cap long-term price growth")
  }

  // Liquidity
  if (s.liquidity != null) {
    if (s.liquidity >= 5)
      reasons.push("Booster boxes sell quickly with high demand — easy to exit position if needed")
    else if (s.liquidity <= 2)
      reasons.push("Slow-moving product — harder to sell, longer hold period likely required")
  }

  // Set depth
  if (s.set_depth != null) {
    if (s.set_depth >= 5)
      reasons.push("Many Illustration Rares across the set — multiple chase tiers support sustained value")
    else if (s.set_depth <= 2)
      reasons.push("Only 1–2 key cards drive most of the value — high pull-rate dependency")
  }

  // Price vs value sanity check
  if (s.bb_price_gbp && s.set_value_gbp) {
    const diff = s.bb_price_gbp - s.set_value_gbp
    if (diff > 0)
      reasons.push(`Box costs £${diff.toFixed(0)} more than total set value — requires price appreciation to break even`)
    else
      reasons.push(`Box costs £${Math.abs(diff).toFixed(0)} less than total set value — positive spread at current prices`)
  }

  return reasons
}

// ── Date parsing for sorting ──────────────────────────────────────────────────
const MONTH_MAP: Record<string, number> = {
  jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
  jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12
}

export function parseDateReleased(dateStr: string | null): number {
  if (!dateStr) return 0
  // Format: "Nov-20", "Jul-25", "Feb-22" etc
  const parts = dateStr.toLowerCase().split("-")
  if (parts.length !== 2) return 0
  const month = MONTH_MAP[parts[0]] ?? 0
  const year  = parseInt(parts[1]) + 2000
  return year * 100 + month
}
