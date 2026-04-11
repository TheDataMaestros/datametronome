import { apiService } from './api'

export interface AppSetting {
  key: string
  value: string
  updated_at: string
}

class SettingsService {
  private readonly endpoint = '/settings'

  async getAll(): Promise<AppSetting[]> {
    const response = await apiService.get<AppSetting[]>(`${this.endpoint}/`)
    return response.data || []
  }

  async get(key: string): Promise<AppSetting> {
    const response = await apiService.get<AppSetting>(`${this.endpoint}/${key}`)
    return response.data
  }

  async set(key: string, value: string): Promise<AppSetting> {
    const response = await apiService.put<AppSetting>(`${this.endpoint}/${key}`, { value })
    return response.data
  }

  async remove(key: string): Promise<void> {
    await apiService.delete(`${this.endpoint}/${key}`)
  }
}

export const settingsService = new SettingsService()
