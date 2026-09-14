import { apiService } from './api'

export interface Group {
  id: string
  name: string
}

class GroupsService {
  private readonly endpoint = '/groups'

  /** Groups the current user belongs to. Determines which staves they can edit. */
  async getMine(): Promise<Group[]> {
    const response = await apiService.get<Group[]>(`${this.endpoint}/mine`)
    return response.data || []
  }
}

export const groupsService = new GroupsService()
