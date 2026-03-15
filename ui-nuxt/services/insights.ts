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
  resolved_at: string | null
  read_at: string | null
  read_by: string | null
  dismiss_reason: string | null
  assigned_to: string | null
  assigned_at: string | null
  created_at: string
}

export interface InsightReport {
  id: string
  stave_id: string
  report_type: string
  health_score: number
  dimensions: { name: string; label?: string; score: number; trend?: string; delta?: number; details?: string }[]
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
  dimensions: { name: string; label?: string; score: number; trend?: string; delta?: number; details?: string }[]
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

export interface InsightNotification {
  id: string
  user_id: string
  type: string
  title: string
  body: string
  reference_type: string
  reference_id: string | null
  read_at: string | null
  created_at: string
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

  async markRead(staveId: string, suggestionId: string, username: string = 'admin'): Promise<void> {
    await apiService.post(`/insights/${staveId}/suggestions/${suggestionId}/read?username=${encodeURIComponent(username)}`, {})
  }

  async assign(staveId: string, suggestionId: string, assignedTo: string): Promise<void> {
    await apiService.post(`/insights/${staveId}/suggestions/${suggestionId}/assign`, { assigned_to: assignedTo })
  }

  async acceptSuggestion(staveId: string, suggestionId: string): Promise<void> {
    await apiService.post(`/insights/${staveId}/suggestions/${suggestionId}/accept`, {})
  }

  async dismissSuggestion(staveId: string, suggestionId: string, reason?: string): Promise<void> {
    await apiService.post(`/insights/${staveId}/suggestions/${suggestionId}/dismiss`, { reason: reason ?? null })
  }

  async triggerAnalysis(staveId: string): Promise<{ task_id: string; status: string }> {
    const response = await apiService.post<{ task_id: string; status: string }>(
      `/insights/${staveId}/analyze`,
      {},
    )
    return response.data
  }

  async pollAnalysis(staveId: string, taskId: string): Promise<{ status: string; report_id?: string }> {
    const response = await apiService.get<{ task_id: string; status: string; report_id?: string }>(
      `/insights/${staveId}/analyze/${taskId}`,
    )
    return response.data
  }

  async getNotifications(userId: string, unreadOnly = false): Promise<InsightNotification[]> {
    const params = unreadOnly ? '?unread_only=true' : ''
    const response = await apiService.get<InsightNotification[]>(`/insights/notifications/${userId}${params}`)
    return response.data
  }

  async markNotificationRead(notificationId: string): Promise<void> {
    await apiService.post(`/insights/notifications/${notificationId}/read`, {})
  }
}

export const insightsService = new InsightsService()
