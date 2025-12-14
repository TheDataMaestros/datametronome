import { ref, computed, readonly } from 'vue'
import { trendsService, type StaveTrends, type TrendsOverview, type TrendDataPoint } from '../services/trends'

export const useTrends = () => {
  const trendsData = ref<StaveTrends | null>(null)
  const overviewData = ref<TrendsOverview | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchStaveTrends = async (
    staveId: string,
    days: number = 7,
    granularity: string = 'hour'
  ) => {
    isLoading.value = true
    error.value = null

    try {
      trendsData.value = await trendsService.getStaveTrends(staveId, days, granularity)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch trends data'
      console.error('Error fetching trends:', err)
    } finally {
      isLoading.value = false
    }
  }

  const fetchTrendsOverview = async (days: number = 7) => {
    isLoading.value = true
    error.value = null

    try {
      console.log('Fetching trends overview...')
      overviewData.value = await trendsService.getTrendsOverview(days)
      console.log('Overview data received:', overviewData.value)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch trends overview'
      console.error('Error fetching trends overview:', err)
    } finally {
      isLoading.value = false
    }
  }

  // Computed properties for chart data
  const chartData = computed(() => {
    if (!trendsData.value?.row_count_trends) return null

    return {
      labels: trendsData.value.row_count_trends.map(point =>
        new Date(point.timestamp).toLocaleString()
      ),
      datasets: [{
        label: 'Row Count',
        data: trendsData.value.row_count_trends.map(point => point.row_count),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.1
      }]
    }
  })

  const statusChartData = computed(() => {
    if (!trendsData.value?.distribution_changes) return null

    const distribution = trendsData.value.distribution_changes.status_distribution
    return {
      labels: Object.keys(distribution),
      datasets: [{
        label: 'Check Status',
        data: Object.values(distribution),
        backgroundColor: [
          'rgb(34, 197, 94)', // green for passed
          'rgb(239, 68, 68)', // red for failed
          'rgb(245, 158, 11)', // yellow for warning
          'rgb(107, 114, 128)' // gray for other
        ]
      }]
    }
  })

  const trendSummary = computed(() => {
    if (!trendsData.value?.trend_summary) return null

    const summary = trendsData.value.trend_summary
    return {
      successRate: summary.success_rate,
      rowCountTrend: summary.row_count_trend,
      overallStatus: summary.overall_status,
      totalDataPoints: summary.total_data_points
    }
  })

  const hasData = computed(() => {
    return !!trendsData.value && (
      (trendsData.value.row_count_trends?.length > 0) ||
      (trendsData.value.check_results?.length > 0) ||
      (trendsData.value.recent_anomalies?.length > 0)
    )
  })

  const getTrendDirection = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return { icon: 'i-heroicons-arrow-trending-up', color: 'text-green-500' }
      case 'decreasing':
        return { icon: 'i-heroicons-arrow-trending-down', color: 'text-red-500' }
      default:
        return { icon: 'i-heroicons-minus', color: 'text-gray-500' }
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return 'text-green-600 bg-green-50'
      case 'failed':
        return 'text-red-600 bg-red-50'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return {
    // State
    trendsData: readonly(trendsData),
    overviewData: readonly(overviewData),
    isLoading: readonly(isLoading),
    error: readonly(error),

    // Computed
    chartData,
    statusChartData,
    trendSummary,
    hasData,

    // Actions
    fetchStaveTrends,
    fetchTrendsOverview,
    getTrendDirection,
    getStatusColor,
  }
}
