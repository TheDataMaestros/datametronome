import { apiService } from './api'

export interface DashboardMetrics {
  success_rate: number
  success_rate_change: number
  active_sources: number
  total_sources: number
  active_checks: number
  scheduled_checks: number
  anomalies: number
  distribution: {
    passed?: number
    failed?: number
    warning?: number
  }
  total_checks: number
  checks_24h: number
}

class DashboardService {
  private readonly endpoint = '/metrics/dashboard'

  async getMetrics(): Promise<DashboardMetrics> {
    const response = await apiService.get<DashboardMetrics>(this.endpoint)
    return response.data
  }
}

export const dashboardService = new DashboardService()
