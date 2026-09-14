import { ref, readonly } from 'vue'
import { groupsService, type Group } from '~/services/groups'

/**
 * Groups the signed-in user belongs to.
 *
 * Membership decides which data sources they can edit, so the shell shows it
 * next to the username. An admin belongs to no group in particular and can
 * edit everything, which is why `isSuperAdmin` is reported separately.
 */
export const useMyGroups = () => {
  const groups = ref<Group[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchMyGroups = async () => {
    isLoading.value = true
    error.value = null
    try {
      groups.value = await groupsService.getMine()
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to load groups'
      groups.value = []
    } finally {
      isLoading.value = false
    }
  }

  return {
    groups: readonly(groups),
    isLoading: readonly(isLoading),
    error: readonly(error),
    fetchMyGroups,
  }
}
