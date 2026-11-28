import { supabase } from './supabase'

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')

export async function api<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const { data, error } = await supabase.auth.getSession()

  if (error) throw new Error(error.message)

  const token = data.session?.access_token
  if (!token) throw new Error('Please sign in to access your financial workspace.')

  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 204) return undefined as T

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail = payload?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message ||
          payload?.message ||
          `Request failed (${response.status})`

    throw new Error(message)
  }

  return (payload?.data ?? payload) as T
}

export function money(value: number, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value || 0)
}

export function dateLabel(value?: string) {
  if (!value) return 'Not scheduled'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
}
