import { apiService } from './api'

export interface Check {
  id: string
  stave_id: string
  clef_id: string
  check_type: string
  status: string
  message?: string | null
  details?: Record<string, any> | null
  timestamp: string
  execution_time?: number | null
  anomalies_count?: number | null
  severity?: string | null
  clef_name?: string
  stave_name?: string
  data_source_type?: string
}

export interface ChecksQuery {
  skip?: number
  limit?: number
  status?: string
  severity?: string
  check_type?: string
  stave_id?: string
  clef_id?: string
  started_after?: string
  started_before?: string
}

const buildQueryString = (query: ChecksQuery = {}): string => {
  const params = new URLSearchParams()

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  })

  const queryString = params.toString()
  return queryString ? `?${queryString}` : ''
}

class ChecksService {
  private readonly endpoint = '/checks/'

  async list(query: ChecksQuery = {}): Promise<Check[]> {
    const response = await apiService.get<Check[]>(`${this.endpoint}${buildQueryString(query)}`)
    return response.data
  }

  async getById(id: string): Promise<Check> {
    const response = await apiService.get<Check>(`${this.endpoint}${id}`)
    return response.data
  }
}

export const checksService = new ChecksService()
