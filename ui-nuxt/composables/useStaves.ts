import { ref, computed, readonly } from 'vue'
import {
  stavesService,
  type Stave,
  type CreateStaveRequest,
  type UpdateStaveRequest,
} from '~/services/staves'

export const useStaves = () => {
  const staves = ref<Stave[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchStaves = async () => {
    isLoading.value = true
    error.value = null

    try {
      const result = await stavesService.getAll()
      staves.value = result || []
      // Clear error if fetch succeeds
      if (error.value) {
        error.value = null
      }
    } catch (err: any) {
      // Extract detailed error message
      let errorMessage = 'Failed to fetch staves'
      if (err instanceof Error) {
        errorMessage = err.message
      } else if (err && typeof err === 'object' && 'message' in err) {
        errorMessage = String(err.message)
      } else if (typeof err === 'string') {
        errorMessage = err
      }
      error.value = errorMessage
      staves.value = [] // Clear staves on error
      console.error('Error fetching staves:', err)
    } finally {
      isLoading.value = false
    }
  }

  const createStave = async (staveData: CreateStaveRequest) => {
    isLoading.value = true
    error.value = null

    try {
      const newStave = await stavesService.create(staveData)
      staves.value.push(newStave)
      return newStave
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create stave'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const updateStave = async (id: string, updates: UpdateStaveRequest) => {
    isLoading.value = true
    error.value = null

    try {
      const updatedStave = await stavesService.update(id, updates)
      const index = staves.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        staves.value[index] = updatedStave
      }
      return updatedStave
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update stave'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const deleteStave = async (id: string) => {
    isLoading.value = true
    error.value = null

    try {
      await stavesService.delete(id)
      staves.value = staves.value.filter((s) => s.id !== id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete stave'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const testConnection = async (id: string) => {
    try {
      return await stavesService.testConnection(id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to test connection'
      throw err
    }
  }

  const getStaveById = (id: string) => {
    return staves.value.find((s) => s.id === id)
  }

  const getActiveStaves = computed(() => {
    return staves.value.filter((s) => s.is_active)
  })

  const getStavesByType = (type: string) => {
    return staves.value.filter((s) => s.data_source_type === type)
  }

  return {
    // State
    staves: readonly(staves),
    isLoading: readonly(isLoading),
    error: readonly(error),

    // Computed
    getActiveStaves,

    // Actions
    fetchStaves,
    createStave,
    updateStave,
    deleteStave,
    testConnection,
    getStaveById,
    getStavesByType,
  }
}
