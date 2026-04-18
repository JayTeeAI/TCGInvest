import { NextRequest, NextResponse } from "next/server"

const API_URL = "http://127.0.0.1:8000"
const API_KEY = process.env.API_KEY || ""

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const path = searchParams.get("path") || ""
  const forward = new URLSearchParams(searchParams)
  forward.delete("path")
  const qs = forward.toString() ? `?${forward.toString()}` : ""
  const res = await fetch(`${API_URL}${path}${qs}`, {
    headers: { "X-API-Key": API_KEY },
    cache: "no-store",
  })
  if (!res.ok) return NextResponse.json({ error: res.status }, { status: res.status })
  return NextResponse.json(await res.json())
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const path = searchParams.get("path") || ""
  const body = await request.text()
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY, "Content-Type": "application/json" },
    body,
    cache: "no-store",
  })
  if (!res.ok) return NextResponse.json({ error: res.status }, { status: res.status })
  return NextResponse.json(await res.json())
}
