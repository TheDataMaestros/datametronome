import { ref, computed, readonly } from 'vue'
import { clefsService, type Clef, type CreateClefRequest, type UpdateClefRequest, type RunClefResponse } from '~/services/clefs'
import type { Check } from '~/services/checks'

export const useClefs = () => {
  const clefs = ref<Clef[]>([])
  const checkResults = ref<Check[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchClefs = async () => {
    isLoading.value = true
    error.value = null

    try {
      clefs.value = await clefsService.getAll()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch clefs'
      console.error('Error fetching clefs:', err)
    } finally {
      isLoading.value = false
    }
  }

  const fetchClefsByStave = async (staveId: string) => {
    isLoading.value = true
    error.value = null

    try {
      return await clefsService.getByStaveId(staveId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch clefs for stave'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const createClef = async (clefData: CreateClefRequest) => {
    isLoading.value = true
    error.value = null

    try {
      const newClef = await clefsService.create(clefData)
      clefs.value.push(newClef)
      return newClef
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create clef'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const updateClef = async (id: string, updates: UpdateClefRequest) => {
    isLoading.value = true
    error.value = null

    try {
      const updatedClef = await clefsService.update(id, updates)
      const index = clefs.value.findIndex(c => c.id === id)
      if (index !== -1) {
        clefs.value[index] = updatedClef
      }
      return updatedClef
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update clef'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const deleteClef = async (id: string) => {
    isLoading.value = true
    error.value = null

    try {
      await clefsService.delete(id)
      clefs.value = clefs.value.filter(c => c.id !== id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete clef'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const runCheck = async (id: string): Promise<RunClefResponse> => {
    try {
      return await clefsService.runCheck(id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to run check'
      throw err
    }
  }

  const fetchCheckResults = async (clefId: string, limit = 50) => {
    try {
      return await clefsService.getResults(clefId, limit)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch check results'
      throw err
    }
  }

  const fetchLatestResults = async (limit = 20) => {
    isLoading.value = true
    error.value = null

    try {
      checkResults.value = await clefsService.getLatestResults(limit)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch latest results'
      console.error('Error fetching latest results:', err)
    } finally {
      isLoading.value = false
    }
  }

  const getClefById = (id: string) => {
    return clefs.value.find(c => c.id === id)
  }

  const getActiveClefs = computed(() => {
    return clefs.value.filter(c => c.is_active)
  })

  const getClefsByType = (type: string) => {
    return clefs.value.filter(c => c.check_type === type)
  }

  const getFailedChecks = computed(() => {
    return checkResults.value.filter(r => r.status?.toLowerCase() === 'fail' || r.status?.toLowerCase() === 'failed')
  })

  const getPassedChecks = computed(() => {
    return checkResults.value.filter(r => r.status?.toLowerCase() === 'pass' || r.status?.toLowerCase() === 'passed')
  })

  const getWarningChecks = computed(() => {
    return checkResults.value.filter(r => {
      const status = r.status?.toLowerCase()
      return status === 'warn' || status === 'warning'
    })
  })

  return {
    // State
    clefs: readonly(clefs),
    checkResults: readonly(checkResults),
    isLoading: readonly(isLoading),
    error: readonly(error),

    // Computed
    getActiveClefs,
    getFailedChecks,
    getPassedChecks,
    getWarningChecks,

    // Actions
    fetchClefs,
    fetchClefsByStave,
    createClef,
    updateClef,
    deleteClef,
    runCheck,
    fetchCheckResults,
    fetchLatestResults,
    getClefById,
    getClefsByType,
  }
}
