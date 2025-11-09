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

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = buildApiUrl(endpoint)
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
    }

    // Add auth token if available
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${authStore.token}`,
      }
    }

    try {
      const response = await fetch(url, config)
      console.log(`API Response [${endpoint}]:`, response.status, response.statusText)
      
      const data = await response.json()
      console.log(`API Data [${endpoint}]:`, data)

      if (!response.ok) {
        throw new Error(data.message || `HTTP ${response.status}`)
      }

      return {
        data,
        status: response.status,
      }
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error)
      throw {
        message: error instanceof Error ? error.message : 'Unknown error',
        status: 500,
        details: error,
      } as ApiError
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
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
