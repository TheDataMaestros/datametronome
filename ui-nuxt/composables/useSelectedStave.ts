// ui-nuxt/composables/useSelectedStave.ts
// Module-level singleton — shared across layout and pages

const selectedStaveId = ref<string | null>(null)
const scopedDashboard = ref<any>(null)
const scopedProfile = ref<any>(null)
const isScopedLoading = ref(false)

export function useSelectedStave() {
  async function selectStave(staveId: string | null) {
    selectedStaveId.value = staveId
    if (!staveId) {
      scopedDashboard.value = null
      scopedProfile.value = null
      return
    }
    isScopedLoading.value = true
    try {
      const { insightsService } = await import('~/services/insights')
      const [dashboard, profile] = await Promise.allSettled([
        insightsService.getDashboard(staveId),
        insightsService.getProfile(staveId),
      ])
      scopedDashboard.value = dashboard.status === 'fulfilled' ? dashboard.value : null
      scopedProfile.value = profile.status === 'fulfilled' ? profile.value : null
    } finally {
      isScopedLoading.value = false
    }
  }

  return {
    selectedStaveId,
    scopedDashboard,
    scopedProfile,
    isScopedLoading,
    selectStave,
  }
}
