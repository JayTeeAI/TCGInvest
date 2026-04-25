export interface BlogPost {
  id?: number
  slug: string
  title: string
  description: string
  date: string
  category: "movers" | "guide" | "analysis"
  readTime: number
  featured?: boolean
  content_md?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY  = process.env.API_KEY || ""

export async function fetchPosts(limit = 20): Promise<BlogPost[]> {
  try {
    const res = await fetch(`${API_BASE}/api/blog?limit=${limit}`, {
      headers: { "X-API-Key": API_KEY },
      next: { revalidate: 3600 },
    })
    if (!res.ok) return []
    const data = await res.json()
    return (data.posts ?? []).map((p: any) => ({
      id:          p.id,
      slug:        p.slug,
      title:       p.title,
      description: p.description,
      date:        p.date,
      category:    p.category,
      readTime:    p.read_time,
      featured:    p.featured,
    }))
  } catch {
    return []
  }
}

export async function fetchPost(slug: string): Promise<BlogPost | null> {
  try {
    const res = await fetch(`${API_BASE}/api/blog/${slug}`, {
      headers: { "X-API-Key": API_KEY },
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    const p = await res.json()
    return {
      id:          p.id,
      slug:        p.slug,
      title:       p.title,
      description: p.description,
      date:        p.date,
      category:    p.category,
      readTime:    p.read_time,
      featured:    p.featured,
      content_md:  p.content_md,
    }
  } catch {
    return null
  }
}

// Legacy compat shims (used nowhere new but keeps any accidental imports safe)
export const posts: BlogPost[] = [
  {
    slug: "pokemon-booster-box-movers-april-2026",
    title: "Pokemon TCG Booster Box Price Movers — April 2026",
    description: "Prismatic Evolutions up 235.2%, Lost Thunder drops 21.9%. This month's biggest sealed product price movements across tracked sets.",
    date: "2026-04-24",
    category: "movers",
    readTime: 4,
    featured: true,
  },]
export function getPost(_slug: string): BlogPost | undefined { return undefined }
export function getLatestPosts(_limit?: number): BlogPost[] { return [] }
