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
              <p class="text-2xl font-bold text-gray-900">{{ formatNumber(summaryMetrics.totalRows) }}</p>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-green-600">+{{ summaryMetrics.totalRowsTrend }}%</span>
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
              <span class="text-sm font-medium text-green-600">+{{ summaryMetrics.qualityTrend }}%</span>
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
              <span class="text-sm font-medium text-red-600">+{{ summaryMetrics.anomalyTrend }}%</span>
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
              <span class="text-sm font-medium text-yellow-600">+{{ summaryMetrics.timeTrend }}%</span>
              <UIcon name="i-heroicons-clock" class="text-yellow-500 ml-1" />
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Charts Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Row Count Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Row Count Trends</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <canvas ref="rowCountChart"></canvas>
          </div>
        </div>
      </UCard>

      <!-- Quality Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Data Quality Trends</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <canvas ref="qualityChart"></canvas>
          </div>
        </div>
      </UCard>

      <!-- Anomaly Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Anomaly Detection</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <canvas ref="anomalyChart"></canvas>
          </div>
        </div>
      </UCard>

      <!-- Processing Time Chart -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Processing Time</h3>
        </template>
        <div class="p-4">
          <div class="h-64">
            <canvas ref="processingChart"></canvas>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Detailed Multi-Line Chart -->
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold">Comprehensive Overview</h3>
      </template>
      <div class="p-4">
        <div class="h-80">
          <canvas ref="detailedChart"></canvas>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import Chart from 'chart.js/auto'

// Nuxt auto-imports
declare const definePageMeta: any
declare const useHead: any

// Use middleware for authentication
definePageMeta({
  // middleware: 'auth',  // Temporarily disabled for testing
  layout: 'dashboard'
})

useHead({
  title: 'Trends & Patterns - DataMetronome'
})

// Reactive state for summary cards
const summaryMetrics = ref({
  totalRows: 125800,
  totalRowsTrend: 12.5,
  dataQuality: 94.2,
  qualityTrend: 2.1,
  anomalies: 8,
  anomalyTrend: 15.3,
  processingTime: 245,
  timeTrend: 8.7
})

// Refs for chart canvases
const rowCountChart = ref<HTMLCanvasElement | null>(null)
const qualityChart = ref<HTMLCanvasElement | null>(null)
const anomalyChart = ref<HTMLCanvasElement | null>(null)
const processingChart = ref<HTMLCanvasElement | null>(null)
const detailedChart = ref<HTMLCanvasElement | null>(null)

// Chart instances
let rowCountChartInstance: Chart | null = null
let qualityChartInstance: Chart | null = null
let anomalyChartInstance: Chart | null = null
let processingChartInstance: Chart | null = null
let detailedChartInstance: Chart | null = null

// Generate simple fake data
const generateFakeData = (days: number = 7) => {
  const labels: string[] = []
  const rowCountData: number[] = []
  const qualityData: number[] = []
  const anomalyData: number[] = []
  const processingData: number[] = []

  // Expected ranges
  const rowCountExpectedMin: number[] = []
  const rowCountExpectedMax: number[] = []
  const qualityExpectedMin: number[] = []
  const qualityExpectedMax: number[] = []
  const processingExpectedMin: number[] = []
  const processingExpectedMax: number[] = []

  // Base values
  let baseRowCount = 120000
  let baseQuality = 95
  let baseProcessing = 200

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))

    // Generate realistic data with trends
    const trendFactor = Math.sin(i * 0.5) * 0.1
    const randomFactor = (Math.random() - 0.5) * 0.2

    const rowCount = baseRowCount * (1 + trendFactor + randomFactor)
    rowCountData.push(Math.floor(rowCount))

    const quality = baseQuality - (i * 0.1) + (Math.random() - 0.5) * 2
    qualityData.push(Math.max(85, Math.min(100, quality)))

    const anomalyChance = Math.random()
    const anomalyCount = anomalyChance > 0.8 ? Math.floor(Math.random() * 10) + 5 :
                        anomalyChance > 0.6 ? Math.floor(Math.random() * 5) : 0
    anomalyData.push(anomalyCount)

    const processingSpike = Math.random() > 0.9 ? 1.5 : 1
    const processing = baseProcessing * processingSpike + (Math.random() - 0.5) * 50
    processingData.push(Math.floor(Math.max(100, processing)))

    // Expected ranges (tighter ranges to show some outliers)
    rowCountExpectedMin.push(Math.floor(baseRowCount * 0.92))
    rowCountExpectedMax.push(Math.floor(baseRowCount * 1.08))
    qualityExpectedMin.push(92)
    qualityExpectedMax.push(98)
    processingExpectedMin.push(180)
    processingExpectedMax.push(280)
  }

  return {
    labels,
    rowCountData,
    qualityData,
    anomalyData,
    processingData,
    rowCountExpectedMin,
    rowCountExpectedMax,
    qualityExpectedMin,
    qualityExpectedMax,
    processingExpectedMin,
    processingExpectedMax
  }
}

// Simple chart creation function
const createChart = (canvas: HTMLCanvasElement, type: string, data: any, options: any = {}) => {
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  // Destroy existing chart if it exists
  if (canvas === rowCountChart.value && rowCountChartInstance) {
    rowCountChartInstance.destroy()
  } else if (canvas === qualityChart.value && qualityChartInstance) {
    qualityChartInstance.destroy()
  } else if (canvas === anomalyChart.value && anomalyChartInstance) {
    anomalyChartInstance.destroy()
  } else if (canvas === processingChart.value && processingChartInstance) {
    processingChartInstance.destroy()
  } else if (canvas === detailedChart.value && detailedChartInstance) {
    detailedChartInstance.destroy()
  }

  const chartInstance = new Chart(ctx, {
    type: type as any,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: 'white',
          bodyColor: 'white',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          cornerRadius: 8
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          },
          ticks: {
            callback: function(value) {
              return formatNumber(value as number)
            }
          }
        }
      },
      ...options
    }
  })

  // Store instance
  if (canvas === rowCountChart.value) rowCountChartInstance = chartInstance
  else if (canvas === qualityChart.value) qualityChartInstance = chartInstance
  else if (canvas === anomalyChart.value) anomalyChartInstance = chartInstance
  else if (canvas === processingChart.value) processingChartInstance = chartInstance
  else if (canvas === detailedChart.value) detailedChartInstance = chartInstance

  return chartInstance
}

// Initialize all charts
const initializeCharts = async () => {
  await nextTick()

  const {
    labels,
    rowCountData,
    qualityData,
    anomalyData,
    processingData,
    rowCountExpectedMin,
    rowCountExpectedMax,
    qualityExpectedMin,
    qualityExpectedMax,
    processingExpectedMin,
    processingExpectedMax
  } = generateFakeData(7)

  // Row Count Chart with Expected Range
  if (rowCountChart.value) {
    createChart(rowCountChart.value, 'line', {
      labels,
      datasets: [
        {
          label: 'Expected Range',
          data: rowCountExpectedMax,
          borderColor: 'rgba(156, 163, 175, 0.3)',
          backgroundColor: 'rgba(156, 163, 175, 0.1)',
          borderWidth: 1,
          fill: '+1',
          tension: 0,
          pointRadius: 0
        },
        {
          label: 'Expected Range Min',
          data: rowCountExpectedMin,
          borderColor: 'rgba(156, 163, 175, 0.3)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          fill: false,
          tension: 0,
          pointRadius: 0
        },
        {
          label: 'Actual Row Count',
          data: rowCountData,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 3,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    })
  }

  // Quality Chart with Expected Range
  if (qualityChart.value) {
    createChart(qualityChart.value, 'line', {
      labels,
      datasets: [
        {
          label: 'Expected Range',
          data: qualityExpectedMax,
          borderColor: 'rgba(156, 163, 175, 0.3)',
          backgroundColor: 'rgba(156, 163, 175, 0.1)',
          borderWidth: 1,
          fill: '+1',
          tension: 0,
          pointRadius: 0
        },
        {
          label: 'Expected Range Min',
          data: qualityExpectedMin,
          borderColor: 'rgba(156, 163, 175, 0.3)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          fill: false,
          tension: 0,
          pointRadius: 0
        },
        {
          label: 'Data Quality %',
          data: qualityData,
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          borderWidth: 3,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    })
  }

  // Anomaly Chart with Threshold
  if (anomalyChart.value) {
    const anomalyThreshold = 5
    createChart(anomalyChart.value, 'bar', {
      labels,
      datasets: [
        {
          label: 'Anomaly Threshold',
          data: new Array(labels.length).fill(anomalyThreshold),
          type: 'line',
          borderColor: 'rgba(239, 68, 68, 0.5)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        },
        {
          label: 'Anomalies Detected',
          data: anomalyData,
          backgroundColor: anomalyData.map((value) =>
            value > anomalyThreshold ? 'rgba(239, 68, 68, 0.8)' :
            value > 0 ? 'rgba(245, 158, 11, 0.8)' :
            'rgba(34, 197, 94, 0.8)'
          ),
          borderColor: anomalyData.map((value) =>
            value > anomalyThreshold ? 'rgb(239, 68, 68)' :
            value > 0 ? 'rgb(245, 158, 11)' :
            'rgb(34, 197, 94)'
          ),
          borderWidth: 2,
          borderRadius: 4
        }
      ]
    })
  }

  // Processing Time Chart with Expected Range
  if (processingChart.value) {
    createChart(processingChart.value, 'line', {
      labels,
      datasets: [
        {
          label: 'Expected Range',
          data: processingExpectedMax,
          borderColor: 'rgba(156, 163, 175, 0.3)',
          backgroundColor: 'rgba(156, 163, 175, 0.1)',
          borderWidth: 1,
          fill: '+1',
          tension: 0,
          pointRadius: 0
        },
        {
          label: 'Expected Range Min',
          data: processingExpectedMin,
          borderColor: 'rgba(156, 163, 175, 0.3)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          fill: false,
          tension: 0,
          pointRadius: 0
        },
        {
          label: 'Processing Time (ms)',
          data: processingData,
          borderColor: 'rgb(245, 158, 11)',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          borderWidth: 3,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    })
  }

  // Detailed Chart (multi-line)
  if (detailedChart.value) {
    createChart(detailedChart.value, 'line', {
      labels,
      datasets: [
        {
          label: 'Row Count',
          data: rowCountData,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 3,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          yAxisID: 'y'
        },
        {
          label: 'Data Quality %',
          data: qualityData,
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          borderWidth: 3,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          yAxisID: 'y1'
        }
      ]
    }, {
      scales: {
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: {
            display: true,
            text: 'Row Count',
            color: 'rgb(59, 130, 246)'
          },
          ticks: {
            color: 'rgb(59, 130, 246)',
            callback: function(value) {
              return formatNumber(value as number)
            }
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: {
            display: true,
            text: 'Data Quality %',
            color: 'rgb(34, 197, 94)'
          },
          ticks: {
            color: 'rgb(34, 197, 94)',
            callback: function(value) {
              return value + '%'
            }
          },
          grid: {
            drawOnChartArea: false,
          },
        }
      }
    })
  }
}

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

// Lifecycle hooks
onMounted(() => {
  initializeCharts()
})

// Refresh data function
const refreshData = () => {
  initializeCharts()
}
</script>
