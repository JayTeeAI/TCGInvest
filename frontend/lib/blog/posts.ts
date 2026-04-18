export interface BlogPost {
  slug: string
  title: string
  description: string
  date: string
  category: "movers" | "guide" | "analysis"
  readTime: number
  featured?: boolean
}

export interface PostSection {
  heading?: string
  body: string
}

export interface FullPost extends BlogPost {
  sections: PostSection[]
  ctaText?: string
  ctaHref?: string
}

export const posts: BlogPost[] = [
  {
    slug: "pokemon-booster-box-movers-april-2026",
    title: "Pokemon TCG Booster Box Price Movers — April 2026",
    description: "Prismatic Evolutions up 235%, Lost Thunder drops 22%. This month\'s biggest sealed product price movements tracked across 43 sets.",
    date: "2026-04-15",
    category: "movers",
    readTime: 4,
    featured: true,
  },
  {
    slug: "best-booster-boxes-to-hold-2026",
    title: "Best Pokemon Booster Boxes to Hold in 2026",
    description: "AI-scored rankings of the top Pokemon TCG booster boxes for long-term investment. Based on scarcity, liquidity, mascot power and set depth across 43 tracked sets.",
    date: "2026-04-15",
    category: "guide",
    readTime: 6,
    featured: true,
  },
  {
    slug: "best-pokemon-centre-etbs-to-hold-2026",
    title: "Best Pokemon Centre ETBs to Hold in 2026",
    description: "Ranked by sealed premium, PSA 10 grading upside and promo card desirability. Which of the 27 Pokemon Centre exclusive ETBs offer the best investment case right now?",
    date: "2026-04-15",
    category: "guide",
    readTime: 5,
    featured: true,
  },
]

export function getPost(slug: string): BlogPost | undefined {
  return posts.find(p => p.slug === slug)
}

export function getLatestPosts(limit?: number): BlogPost[] {
  const sorted = [...posts].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  return limit ? sorted.slice(0, limit) : sorted
}
