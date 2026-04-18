import { cookies } from "next/headers"

export interface User {
  authenticated: boolean
  email?: string
  role?: 'free' | 'premium' | 'admin'
  user_id?: string
}

export async function getUser(): Promise<User> {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get('auth_token')
    const res = await fetch('http://localhost:8000/auth/me', {
      cache: 'no-store',
      headers: token ? { Cookie: `auth_token=${token.value}` } : {},
    })
    if (!res.ok) return { authenticated: false }
    return res.json()
  } catch {
    return { authenticated: false }
  }
}
