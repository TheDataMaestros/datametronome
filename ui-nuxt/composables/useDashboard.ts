import { ref, readonly } from 'vue'
import { dashboardService, type DashboardMetrics } from '~/services/dashboard'

export const useDashboard = () => {
  const metrics = ref<DashboardMetrics | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchMetrics = async () => {
    isLoading.value = true
    error.value = null

    try {
      metrics.value = await dashboardService.getMetrics()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch dashboard metrics'
      console.error('Error fetching dashboard metrics:', err)
      // Set default values on error
      metrics.value = {
        success_rate: 0,
        success_rate_change: 0,
        active_sources: 0,
        total_sources: 0,
        active_checks: 0,
        scheduled_checks: 0,
        anomalies: 0,
        distribution: {},
        total_checks: 0,
        checks_24h: 0,
      }
    } finally {
      isLoading.value = false
    }
  }

  return {
    metrics: readonly(metrics),
    isLoading: readonly(isLoading),
    error: readonly(error),
    fetchMetrics,
  }
}
