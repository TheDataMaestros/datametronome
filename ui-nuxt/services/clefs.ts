import { apiService, type ApiResponse } from './api'

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

export interface CheckResult {
  id: string
  clef_id: string
  status: 'passed' | 'failed' | 'warning'
  message?: string
  executed_at: string
  execution_time_ms: number
  details?: Record<string, any>
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

  async runCheck(id: string): Promise<CheckResult> {
    const response = await apiService.post<CheckResult>(`${this.endpoint}/${id}/run`)
    return response.data
  }

  async getResults(id: string, limit = 50): Promise<CheckResult[]> {
    const response = await apiService.get<CheckResult[]>(`${this.endpoint}/${id}/results?limit=${limit}`)
    return response.data
  }

  async getLatestResults(): Promise<CheckResult[]> {
    const response = await apiService.get<CheckResult[]>('/check-results/latest')
    return response.data
  }
}

export const clefsService = new ClefsService()
