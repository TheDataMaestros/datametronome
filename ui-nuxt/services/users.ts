import { apiService } from './api'

export interface UserDetail {
  id: string
  username: string
  email: string
  is_active: boolean
  role: 'admin' | 'editor' | 'viewer'
  created_at: string
  updated_at: string
}

export interface CreateUserPayload {
  username: string
  email: string
  password: string
  role: 'admin' | 'editor' | 'viewer'
}

export interface UpdateUserPayload {
  email?: string
  role?: 'admin' | 'editor' | 'viewer'
  is_active?: boolean
}

class UsersService {
  private readonly endpoint = '/users'

  async getAll(): Promise<UserDetail[]> {
    const response = await apiService.get<UserDetail[]>(`${this.endpoint}/`)
    return response.data || []
  }

  async get(id: string): Promise<UserDetail> {
    const response = await apiService.get<UserDetail>(`${this.endpoint}/${id}`)
    return response.data
  }

  async create(payload: CreateUserPayload): Promise<UserDetail> {
    const response = await apiService.post<UserDetail>(`${this.endpoint}/`, payload)
    return response.data
  }

  async update(id: string, payload: UpdateUserPayload): Promise<UserDetail> {
    const response = await apiService.patch<UserDetail>(`${this.endpoint}/${id}`, payload)
    return response.data
  }

  async resetPassword(id: string, newPassword: string): Promise<void> {
    await apiService.post(`${this.endpoint}/${id}/reset-password`, { new_password: newPassword })
  }

  async remove(id: string, hard = false): Promise<void> {
    const query = hard ? '?hard=true' : ''
    await apiService.delete(`${this.endpoint}/${id}${query}`)
  }
}

export const usersService = new UsersService()
