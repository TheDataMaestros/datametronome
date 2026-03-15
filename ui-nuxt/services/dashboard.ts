import { apiService } from './api'

export interface IntelligenceSuggestion {
  priority: string
  category: string
  action: string
  reasoning: string
}

export interface IntelligenceAnomaly {
  severity: string
  category: string
  description: string
  table: string
  evidence: string
  detected_at: string | null
  snapshot_at: string | null
}

export interface IntelligenceMetrics {
  avg_health_score: number
  total_reports: number
  profiled_sources: number
  pending_suggestions: number
  insight_anomalies: number
  critical_anomalies: number
  top_suggestions: IntelligenceSuggestion[]
  top_anomalies: IntelligenceAnomaly[]
  last_analyzed_at: string | null
  table_metrics: Record<string, number>
}

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
  intelligence?: IntelligenceMetrics
}

class DashboardService {
  private readonly endpoint = '/metrics/dashboard'

  async getMetrics(): Promise<DashboardMetrics> {
    const response = await apiService.get<DashboardMetrics>(this.endpoint)
    return response.data
  }
}

export const dashboardService = new DashboardService()
