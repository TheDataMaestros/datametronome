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

/**
 * Parse the S3 "tables" textarea into the mapping the API expects.
 *
 * Users type one `name = path` per line. The API wants
 * `{"users": "users/*.parquet"}`. Paths contain `=` in Hive-style partition
 * globs (`orders/dt=*&#47;*.parquet`), so only the first `=` separates the two.
 *
 * Returns the parsed mapping, or an error naming the offending line.
 */
export function parseS3Tables(
  input: string,
): { tables: Record<string, string> } | { error: string } {
  const tables: Record<string, string> = {}

  const lines = (input || '').split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line || line.startsWith('#')) continue

    const split = line.indexOf('=')
    if (split === -1) {
      return { error: `Line ${i + 1} is missing "=": ${line}` }
    }

    const name = line.slice(0, split).trim()
    const path = line.slice(split + 1).trim()

    if (!name) return { error: `Line ${i + 1} has no table name` }
    if (!path) return { error: `Table "${name}" has no path` }
    // The name is interpolated into CREATE VIEW server-side, which rejects
    // anything that is not a plain identifier. Say so here instead.
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
      return {
        error: `Table name "${name}" must be letters, digits and underscores, starting with a letter`,
      }
    }
    if (tables[name]) return { error: `Table "${name}" is listed twice` }

    tables[name] = path
  }

  if (Object.keys(tables).length === 0) {
    return { error: 'Add at least one table, e.g. users = users/*.parquet' }
  }

  return { tables }
}

class StavesService {
  private readonly endpoint = '/staves'

  async getAll(): Promise<Stave[]> {
    const response = await apiService.get<Stave[]>(`${this.endpoint}/`)
    return response.data || []
  }

  async getById(id: string): Promise<Stave> {
    const response = await apiService.get<Stave>(`${this.endpoint}/${id}`)
    return response.data
  }

  async create(stave: CreateStaveRequest): Promise<Stave> {
    const response = await apiService.post<Stave>(`${this.endpoint}/`, stave)
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
      `${this.endpoint}/${id}/test-connection`,
    )
    return response.data
  }

  async getClefs(id: string): Promise<any[]> {
    const response = await apiService.get<any[]>(`${this.endpoint}/${id}/clefs`)
    return response.data
  }

  async getAvailableTypes(): Promise<string[]> {
    const response = await apiService.get<string[]>('/staves/types')
    return response.data
  }
}

export const stavesService = new StavesService()
