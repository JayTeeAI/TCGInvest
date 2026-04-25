const SERVER_URL = "http://127.0.0.1:8000"
const API_KEY = process.env.API_KEY || ""

function isServer() {
  return typeof window === "undefined"
}

async function apiFetch(path: string) {
  let url: string
  let headers: Record<string, string> = {}

  if (isServer()) {
    url = `${SERVER_URL}${path}`
    headers = { "X-API-Key": API_KEY }
  } else {
    const encoded = encodeURIComponent(path)
    url = `/api/internal?path=${encoded}`
  }

  const res = await fetch(url, { headers, cache: "no-store" })
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`)
  return res.json()
}

export async function getSets(params?: {
  era?: string
  recommendation?: string
  min_score?: number
  max_box_pct?: number
  run_date?: string
}) {
  const query = new URLSearchParams()
  if (params?.era)            query.set("era", params.era)
  if (params?.recommendation) query.set("recommendation", params.recommendation)
  if (params?.min_score)      query.set("min_score", String(params.min_score))
  if (params?.max_box_pct)    query.set("max_box_pct", String(params.max_box_pct))
  if (params?.run_date)       query.set("run_date", params.run_date)
  const qs = query.toString() ? `?${query.toString()}` : ""
  return apiFetch(`/api/sets${qs}`)
}

export async function getSummary() {
  return apiFetch("/api/summary")
}

export async function getSetHistory(setName: string) {
  return apiFetch(`/api/sets/${encodeURIComponent(setName)}/history`)
}

export async function getSetCardPriceHistory(setName: string) {
  return apiFetch(`/api/sets/${encodeURIComponent(setName)}/card-price-history`)
}

export async function getSetCardPriceHistoryDaily(setName: string) {
  return apiFetch(`/api/sets/${encodeURIComponent(setName)}/card-price-history-daily`)
}

export async function getSetBBPriceHistoryDaily(setId: number) {
  return apiFetch(`/api/sets/${setId}/bb-price-history-daily`)
}

export async function getTools() {
  return apiFetch("/api/tools")
}

export async function getRunDates() {
  return apiFetch("/api/sets/run-dates")
}

export async function getMovers() {
  return apiFetch("/api/movers")
}

export async function getCurrentPrice(setName: string) {
  return apiFetch(`/api/roi-calculator/current-price?set_name=${encodeURIComponent(setName)}`)
}

export async function getETBs(snapshotDate?: string) {
  const qs = snapshotDate ? `?snapshot_date=${encodeURIComponent(snapshotDate)}` : ""
  return apiFetch(`/api/etbs${qs}`)
}

export async function getETBHistory(etbId: number) {
  return apiFetch(`/api/etbs/${etbId}/history`)
}

export async function getETBSnapshotDates() {
  return apiFetch("/api/etb/snapshot-dates")
}

export async function getETBMovers() {
  return apiFetch("/api/etb-movers")
}

export async function getChaseMovers() {
  return apiFetch("/api/chase-movers")
}

export async function getChaseCards() {
  return apiFetch("/api/chase-cards")
}

export async function getChaseCard(id: number | string) {
  return apiFetch(`/api/chase-cards/${id}`)
}

export async function getChaseCardHistory(id: number | string) {
  return apiFetch(`/api/chase-cards/${id}/history`)
}

export async function getSetMomentum(setId: number) {
  return apiFetch(`/api/sets/${setId}/momentum`)
}

export async function getSetHeat(setId: number) {
  return apiFetch(`/api/sets/${setId}/heat`)
}

export async function getHeatScores() {
  return apiFetch("/api/heat-scores")
}
