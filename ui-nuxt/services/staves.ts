import { apiService, type ApiResponse } from './api'

export interface Stave {
  id: string
  name: string
  description?: string
  data_source_type: string
  is_active: boolean
  created_at: string
  updated_at: string
  connection_config: Record<string, any>
}

export interface CreateStaveRequest {
  name: string
  description?: string
  data_source_type: string
  connection_config: Record<string, any>
}

export interface UpdateStaveRequest extends Partial<CreateStaveRequest> {
  is_active?: boolean
}

class StavesService {
  private readonly endpoint = '/staves'

  async getAll(): Promise<Stave[]> {
    const response = await apiService.get<Stave[]>(this.endpoint)
    return response.data
  }

  async getById(id: string): Promise<Stave> {
    const response = await apiService.get<Stave>(`${this.endpoint}/${id}`)
    return response.data
  }

  async create(stave: CreateStaveRequest): Promise<Stave> {
    const response = await apiService.post<Stave>(this.endpoint, stave)
    return response.data
  }

  async update(id: string, updates: UpdateStaveRequest): Promise<Stave> {
    const response = await apiService.put<Stave>(`${this.endpoint}/${id}`, updates)
    return response.data
  }

  async delete(id: string): Promise<void> {
    await apiService.delete(`${this.endpoint}/${id}`)
  }

  async testConnection(id: string): Promise<{ success: boolean; message: string }> {
    const response = await apiService.post<{ success: boolean; message: string }>(
      `${this.endpoint}/${id}/test-connection`
    )
    return response.data
  }

  async getClefs(id: string): Promise<any[]> {
    const response = await apiService.get<any[]>(`${this.endpoint}/${id}/clefs`)
    return response.data
  }
}

export const stavesService = new StavesService()
