"use client"

export interface User {
  authenticated: boolean
  email?: string
  role?: 'free' | 'premium' | 'admin'
  user_id?: string
}

export async function getUserClient(): Promise<User> {
  try {
    const res = await fetch('/auth/me', {
      credentials: 'include',
      cache: 'no-store',
    })
    if (!res.ok) return { authenticated: false }
    return res.json()
  } catch {
    return { authenticated: false }
  }
}

export function getGoogleLoginUrl(): string {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://tcginvest.uk'
  return `${API_URL}/auth/google`
}

export async function logout(): Promise<void> {
  await fetch('/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
  window.location.href = '/'
}
