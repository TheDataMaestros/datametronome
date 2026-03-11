import { useAuthStore } from '~/stores/auth'
import { config, buildApiUrl } from '~/config/app'

interface ApiResponse<T = any> {
  data: T
  message?: string
  status: number
}

interface ApiError {
  message: string
  status: number
  details?: any
}

class ApiService {
  private baseURL: string
  private defaultHeaders: Record<string, string>

  constructor() {
    this.baseURL = config.apiBase
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const url = buildApiUrl(endpoint)

    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
      signal: options.signal, // Preserve abort signal
    }

    // Add auth token if available
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${authStore.token}`,
      }
    }

    try {
      const response = await fetch(url, config)

      // Check if request was aborted
      if (config.signal?.aborted) {
        throw new Error('Request aborted')
      }
      console.log(`API Response [${endpoint}]:`, response.status, response.statusText)

      const raw = await response.text()
      let data: any = null
      try {
        data = raw ? JSON.parse(raw) : null
      } catch {
        data = raw
      }
      console.log(`API Data [${endpoint}]:`, data)

      if (!response.ok) {
        // Handle 401 Unauthorized (expired token)
        if (response.status === 401) {
          const authStore = useAuthStore()
          authStore.logout()
          // Redirect to login if not already there
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
            window.location.href = '/login'
          }
        }

        throw {
          message:
            data && typeof data === 'object' && 'detail' in data
              ? (data as any).detail
              : data && typeof data === 'object' && 'message' in data
                ? (data as any).message
                : `HTTP ${response.status}`,
          status: response.status,
          details: data,
        } as ApiError
      }

      return {
        data,
        status: response.status,
      }
    } catch (error) {
      // Check if error is due to abort
      if (error instanceof Error && error.name === 'AbortError') {
        throw error
      }

      console.error(`API Error [${endpoint}]:`, error)
      if (error && typeof error === 'object' && 'status' in error && 'message' in error) {
        throw error as ApiError
      }
      throw {
        message: error instanceof Error ? error.message : 'Network or unknown error',
        status: 0,
        details: error,
      } as ApiError
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: any, signal?: AbortSignal): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      signal,
    })
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiService = new ApiService()
export type { ApiResponse, ApiError }

/** Extract a user-facing error message from API errors or unknown throw values. */
export function extractErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object' && 'message' in err) {
    const m = (err as ApiError).message
    if (typeof m === 'string') return m
    if (Array.isArray(m)) return m.map((e: any) => e?.msg ?? String(e)).filter(Boolean).join('; ') || fallback
  }
  if (err instanceof Error) return err.message
  return fallback
}
