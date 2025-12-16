import { ref, readonly } from 'vue'
import { checksService, type Check, type ChecksQuery } from '~/services/checks'

export const useChecks = () => {
  const checks = ref<Check[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchChecks = async (query: ChecksQuery = {}) => {
    isLoading.value = true
    error.value = null

    try {
      checks.value = await checksService.list(query)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch checks'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchForClef = async (clefId: string, limit = 10) => {
    return fetchChecks({ clef_id: clefId, limit })
  }

  const fetchLatest = async (limit = 20) => {
    return fetchChecks({ limit })
  }

  return {
    checks: readonly(checks),
    isLoading: readonly(isLoading),
    error: readonly(error),
    fetchChecks,
    fetchForClef,
    fetchLatest,
  }
}
