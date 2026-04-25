import { cookies } from 'next/headers'
import PortfolioClient from '../../../components/portfolio/PortfolioClient'

export const metadata = {
  title: 'My Portfolio | TCGInvest',
  description: 'Track your Pokemon TCG sealed product investments — cost basis, current value, and unrealised gains.',
}

async function getRole(): Promise<string> {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('auth_token')
    const res = await fetch('http://127.0.0.1:8000/auth/me', {
      cache: 'no-store',
      headers: token ? { Cookie: 'auth_token=' + token.value } : {},
    })
    if (!res.ok) return 'guest'
    const data = await res.json()
    return data.role ?? 'free'
  } catch {
    return 'guest'
  }
}

export default async function PortfolioPage() {
  const role = await getRole()
  // Don't server-redirect — let the client component handle unauthenticated state
  // so the user sees the page and gets a proper sign-in prompt
  return <PortfolioClient role={role} />
}
