<template>
  <div class="p-6 space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Trends & Patterns</h1>
        <p class="text-gray-600 mt-1">Monitor data trends and detect patterns across your staves</p>
      </div>
      <UButton @click="refreshData" color="primary" variant="solid">
        <UIcon name="i-heroicons-arrow-path" class="mr-2" />
        Refresh Data
      </UButton>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <UCard>
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Total Rows</p>
              <p class="text-2xl font-bold text-gray-900">
                {{ formatNumber(summaryMetrics.totalRows) }}
              </p>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-green-600"
                >+{{ summaryMetrics.totalRowsTrend }}%</span
              >
              <UIcon name="i-heroicons-arrow-trending-up" class="text-green-500 ml-1" />
            </div>
          </div>
        </div>
      </UCard>

      <UCard>
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Data Quality</p>
              <p class="text-2xl font-bold text-gray-900">{{ summaryMetrics.dataQuality }}%</p>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-green-600"
                >+{{ summaryMetrics.qualityTrend }}%</span
              >
              <UIcon name="i-heroicons-arrow-trending-up" class="text-green-500 ml-1" />
            </div>
          </div>
        </div>
      </UCard>

      <UCard>
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Anomalies</p>
              <p class="text-2xl font-bold text-gray-900">{{ summaryMetrics.anomalies }}</p>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-red-600"
                >+{{ summaryMetrics.anomalyTrend }}%</span
              >
              <UIcon name="i-heroicons-exclamation-triangle" class="text-red-500 ml-1" />
            </div>
          </div>
        </div>
      </UCard>

      <UCard>
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Processing Time</p>
              <p class="text-2xl font-bold text-gray-900">{{ summaryMetrics.processingTime }}ms</p>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-yellow-600"
                >+{{ summaryMetrics.timeTrend }}%</span
              >
              <UIcon name="i-heroicons-clock" class="text-yellow-500 ml-1" />
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Charts Grid - Using Real Data -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Row Count Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Row Count Trends</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <CheckTypeChart
              check-type="row_count"
              :data="checkResults"
              :height="250"
              :show-legend="true"
            />
          </div>
        </div>
      </UCard>

      <!-- Column Values Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Data Quality Trends</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <CheckTypeChart
              check-type="column_values"
              :data="checkResults"
              :height="250"
              :show-legend="true"
            />
          </div>
        </div>
      </UCard>

      <!-- Anomaly Detection Chart (Forecast) -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Anomaly Detection (Forecast)</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <CheckTypeChart
              check-type="forecast"
              :data="checkResults"
              :height="250"
              :show-legend="true"
            />
          </div>
        </div>
      </UCard>

      <!-- Data Drift Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Data Drift Detection</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <CheckTypeChart
              check-type="drift"
              :data="checkResults"
              :height="250"
              :show-legend="true"
            />
          </div>
        </div>
      </UCard>
    </div>

    <!-- Freshness Chart -->
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold">Data Freshness Trends</h3>
      </template>
      <div class="p-4">
        <div class="h-80">
          <CheckTypeChart
            check-type="freshness"
            :data="checkResults"
            :height="300"
            :show-legend="true"
          />
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useClefs } from '~/composables/useClefs'

// Nuxt auto-imports
declare const definePageMeta: any
declare const useHead: any

// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({
  title: 'Trends & Patterns - DataMetronome',
})

// Fetch real check results
const { checkResults, fetchLatestResults } = useClefs()

// Reactive state for summary cards
const summaryMetrics = computed(() => {
  const results = checkResults.value || []
  const rowCountChecks = results.filter(
    (r: any) => String(r?.check_type || '').toLowerCase() === 'row_count',
  )
  const qualityChecks = results.filter(
    (r: any) => String(r?.check_type || '').toLowerCase() === 'column_values',
  )
  const anomalyChecks = results.filter(
    (r: any) => String(r?.check_type || '').toLowerCase() === 'forecast',
  )

  const totalRows = rowCountChecks.reduce((sum: number, r: any) => {
    const meta = r?.metadata || r?.details || {}
    return sum + (Number(meta?.row_count ?? meta?.count ?? 0) || 0)
  }, 0)

  const passedChecks = results.filter((r: any) => {
    const status = String(r?.status || '').toLowerCase()
    return status === 'pass' || status === 'passed'
  }).length

  const dataQuality = results.length > 0 ? (passedChecks / results.length) * 100 : 0

  return {
    totalRows,
    totalRowsTrend: 0, // Could calculate from historical data
    dataQuality: Math.round(dataQuality * 10) / 10,
    qualityTrend: 0,
    anomalies: anomalyChecks.filter((r: any) => {
      const status = String(r?.status || '').toLowerCase()
      return status === 'fail' || status === 'warn'
    }).length,
    anomalyTrend: 0,
    processingTime: 0,
    timeTrend: 0,
  }
})

// Utility function
const formatNumber = (num: number) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

// Refresh data function
const refreshData = async () => {
  await fetchLatestResults(100)
}

// Lifecycle hooks
onMounted(async () => {
  await refreshData()
})
</script>
