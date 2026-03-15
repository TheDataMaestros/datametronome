import { apiService } from './api'

export interface InsightAnomaly {
  severity: string
  category: string
  description: string
  table: string
  evidence: string
  compared_to?: string
}

export interface InsightSuggestion {
  id: string
  stave_id: string
  report_id: string
  priority: string
  category: string
  action: string
  reasoning: string
  based_on: string
  status: string
  created_at: string
}

export interface InsightReport {
  id: string
  stave_id: string
  report_type: string
  health_score: number
  dimensions: { name: string; score: number; description?: string }[]
  anomalies: InsightAnomaly[]
  suggestions: { priority: string; category: string; action: string; reasoning: string }[]
  summary: string
  key_findings: string[]
  created_at: string
}

export interface InsightDashboard {
  stave_id: string
  health_score: number
  health_trend: 'improving' | 'declining' | 'stable'
  dimensions: { name: string; score: number; description?: string }[]
  active_anomalies: InsightAnomaly[]
  pending_suggestions: InsightSuggestion[]
  ai_created_checks: { id: string; clef_id: string; rationale: string }[]
  last_analyzed_at: string | null
}

export interface DataProfile {
  id: string
  stave_id: string
  domain_type: string
  domain_confidence: number
  domain_context: { business_context?: string }
  entity_roles: Record<string, string>
  profile_version: number
  created_at: string
  updated_at: string
}

class InsightsService {
  async getDashboard(staveId: string): Promise<InsightDashboard> {
    const response = await apiService.get<InsightDashboard>(`/insights/${staveId}/dashboard`)
    return response.data
  }

  async getLatestReport(staveId: string): Promise<InsightReport> {
    const response = await apiService.get<InsightReport>(`/insights/${staveId}/latest`)
    return response.data
  }

  async getProfile(staveId: string): Promise<DataProfile> {
    const response = await apiService.get<DataProfile>(`/insights/${staveId}/profile`)
    return response.data
  }

  async acceptSuggestion(staveId: string, suggestionId: string): Promise<void> {
    await apiService.post(`/insights/${staveId}/suggestions/${suggestionId}/accept`, {})
  }

  async dismissSuggestion(staveId: string, suggestionId: string): Promise<void> {
    await apiService.post(`/insights/${staveId}/suggestions/${suggestionId}/dismiss`, {})
  }

  async triggerAnalysis(staveId: string): Promise<{ task_id: string; status: string }> {
    const response = await apiService.post<{ task_id: string; status: string }>(
      `/insights/${staveId}/analyze`,
      {},
    )
    return response.data
  }
}

export const insightsService = new InsightsService()
