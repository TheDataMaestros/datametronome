import { apiService } from './api'

export interface Group {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface GroupMember {
  user_id: string
  username: string
  email: string
  role: string
}

class GroupsService {
  private readonly endpoint = '/groups'

  async getAll(): Promise<Group[]> {
    const response = await apiService.get<Group[]>(`${this.endpoint}/`)
    return response.data || []
  }

  /** Groups the current user belongs to. Determines which staves they can edit. */
  async getMine(): Promise<Group[]> {
    const response = await apiService.get<Group[]>(`${this.endpoint}/mine`)
    return response.data || []
  }

  async getMembers(groupId: string): Promise<GroupMember[]> {
    const response = await apiService.get<GroupMember[]>(`${this.endpoint}/${groupId}/members`)
    return response.data || []
  }
}

export const groupsService = new GroupsService()
