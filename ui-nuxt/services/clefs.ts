import { apiService } from './api'
import type { Check } from './checks'

export interface Clef {
  id: string
  name: string
  description?: string
  stave_id: string
  check_type: string
  is_active: boolean
  created_at: string
  updated_at: string
  configuration: Record<string, any>
  schedule?: string
  warn?: string
  fail?: string
}

export interface CreateClefRequest {
  name: string
  description?: string
  stave_id: string
  check_type: string
  configuration: Record<string, any>
  schedule?: string
  is_active?: boolean
  warn?: string
  fail?: string
}

export interface UpdateClefRequest extends Partial<CreateClefRequest> {
  is_active?: boolean
}

export interface RunClefResponse {
  success: boolean
  clef_id: string
  stave_id: string
  status: string
  observed_value?: number | null
  message?: string | null
  execution_time?: number | null
  metadata?: Record<string, any> | null
  check_id?: string
}

class ClefsService {
  private readonly endpoint = '/clefs'

  async getAll(): Promise<Clef[]> {
    const response = await apiService.get<Clef[]>(this.endpoint)
    return response.data
  }

  async getById(id: string): Promise<Clef> {
    const response = await apiService.get<Clef>(`${this.endpoint}/${id}`)
    return response.data
  }

  async getByStaveId(staveId: string): Promise<Clef[]> {
    const response = await apiService.get<Clef[]>(`${this.endpoint}?stave_id=${staveId}`)
    return response.data
  }

  async create(clef: CreateClefRequest): Promise<Clef> {
    const response = await apiService.post<Clef>(this.endpoint, clef)
    return response.data
  }

  async update(id: string, updates: UpdateClefRequest): Promise<Clef> {
    const response = await apiService.put<Clef>(`${this.endpoint}/${id}`, updates)
    return response.data
  }

  async delete(id: string): Promise<void> {
    await apiService.delete(`${this.endpoint}/${id}`)
  }

  async runCheck(id: string): Promise<RunClefResponse> {
    const response = await apiService.post<RunClefResponse>(`${this.endpoint}/${id}/run-now`)
    return response.data
  }

  async getResults(id: string, limit = 50): Promise<Check[]> {
    const response = await apiService.get<{ results: Check[] }>(`${this.endpoint}/${id}/results?limit=${limit}`)
    return response.data.results
  }

  async getLatestResults(limit = 20): Promise<Check[]> {
    const response = await apiService.get<{ results: Check[] }>(`${this.endpoint}/results/latest?limit=${limit}`)
    return response.data.results
  }
}

export const clefsService = new ClefsService()
