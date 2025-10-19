import { apiService, type ApiResponse } from './api'

export interface TrendDataPoint {
  timestamp: string
  row_count: number
  status: string
  raw_timestamp: string
}

export interface CheckResult {
  time_bucket: string
  check_type: string
  status: string
  check_count: number
  avg_execution_time: number
  total_anomalies: number
}

export interface DistributionChange {
  status_distribution: Record<string, number>
  status_percentages: Record<string, number>
  check_type_distribution: Record<string, any>
  total_checks: number
}

export interface TrendSummary {
  success_rate: number
  row_count_trend: string
  total_data_points: number
  overall_status: string
}

export interface StaveTrends {
  stave: {
    id: string
    name: string
    data_source_type: string
  }
  period: {
    days: number
    granularity: string
    start_date: string
    end_date: string
  }
  row_count_trends: TrendDataPoint[]
  check_results: CheckResult[]
  distribution_changes: DistributionChange
  recent_anomalies: any[]
  trend_summary: TrendSummary
}

export interface StaveSummary {
  stave: {
    id: string
    name: string
    data_source_type: string
  }
  check_counts: Record<string, number>
  latest_row_count: number
  last_check: string | null
}

export interface TrendsOverview {
  period: {
    days: number
    start_date: string
    end_date: string
  }
  stave_summaries: StaveSummary[]
  total_staves: number
}

class TrendsService {
  private readonly endpoint = '/trends'

  async getStaveTrends(
    staveId: string, 
    days: number = 7, 
    granularity: string = 'hour'
  ): Promise<StaveTrends> {
    const response = await fetch(`http://localhost:8000/api/v1/trends/stave/${staveId}?days=${days}&granularity=${granularity}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return await response.json()
  }

  async getTrendsOverview(days: number = 7): Promise<TrendsOverview> {
    console.log('Making API call to trends overview...')
    const response = await fetch(`http://localhost:8000/api/v1/trends/overview?days=${days}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    console.log('Response status:', response.status)
    console.log('Response headers:', response.headers)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('API Error:', response.status, errorText)
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    console.log('API Response data:', data)
    return data
  }
}

export const trendsService = new TrendsService()
