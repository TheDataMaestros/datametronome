import { ref, computed } from 'vue'
import { apiService } from '~/services/api'

interface DashboardPrefs {
  pinned_staves: string[]
}

const prefs = ref<DashboardPrefs>({ pinned_staves: [] })
const isPatching = ref(false)

export function useDashboardPrefs() {
  async function loadPrefs() {
    try {
      const response = await apiService.get<{ dashboard_prefs: DashboardPrefs }>('/auth/me')
      prefs.value = response.data.dashboard_prefs ?? { pinned_staves: [] }
    } catch {
      prefs.value = { pinned_staves: [] }
    }
  }

  async function savePrefs(newPrefs: DashboardPrefs) {
    if (isPatching.value) return
    isPatching.value = true
    const previous = { ...prefs.value, pinned_staves: [...prefs.value.pinned_staves] }
    prefs.value = newPrefs // optimistic
    try {
      await apiService.patch('/auth/me', { dashboard_prefs: newPrefs })
    } catch {
      prefs.value = previous // revert on error
      throw new Error('Failed to save preferences')
    } finally {
      isPatching.value = false
    }
  }

  async function pinStave(staveId: string) {
    if (prefs.value.pinned_staves.includes(staveId)) return
    if (prefs.value.pinned_staves.length >= 3) return
    await savePrefs({ pinned_staves: [...prefs.value.pinned_staves, staveId] })
  }

  async function unpinStave(staveId: string) {
    await savePrefs({ pinned_staves: prefs.value.pinned_staves.filter((id) => id !== staveId) })
  }

  async function reorderPinned(newOrder: string[]) {
    await savePrefs({ pinned_staves: newOrder })
  }

  const pinnedStaveIds = computed(() => prefs.value.pinned_staves)
  const hasFavourites = computed(() => prefs.value.pinned_staves.length > 0)
  const atMax = computed(() => prefs.value.pinned_staves.length >= 3)

  return {
    prefs,
    isPatching,
    pinnedStaveIds,
    hasFavourites,
    atMax,
    loadPrefs,
    pinStave,
    unpinStave,
    reorderPinned,
  }
}
