<template>
  <div class="w-full" :style="height ? `height: ${height}px` : 'height: 100%'">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  LineController,
  BarController,
  DoughnutController,
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  LineController,
  BarController,
  DoughnutController,
)

interface ChartData {
  labels: string[]
  datasets: Array<{
    label: string
    data: number[]
    borderColor?: string
    backgroundColor?: string | string[]
    tension?: number
    fill?: boolean
  }>
}

interface TrendDataPoint {
  date: string
  success?: number
  failures?: number
  warnings?: number
  [key: string]: any
}

interface Props {
  data: ChartData | TrendDataPoint[]
  type: 'line' | 'doughnut' | 'bar'
  options?: any
  height?: number
  showLegend?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'line',
  options: () => ({}),
  height: undefined,
  showLegend: true,
})

const chartCanvas = ref<HTMLCanvasElement>()
let chartInstance: ChartJS | null = null

// Transform trend data format to Chart.js format if needed
const chartData = computed(() => {
  // If data is already in Chart.js format (has labels and datasets)
  if (Array.isArray(props.data) && props.data.length > 0 && 'labels' in props.data[0] === false) {
    // It's trend data format - transform it
    const trendData = props.data as TrendDataPoint[]
    const labels = trendData.map((d) => {
      const date = new Date(d.date)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    })

    const datasets: Array<{
      label: string
      data: number[]
      borderColor: string
      backgroundColor: string
      tension: number
      fill: boolean
    }> = []

    if (trendData.some((d) => d.success !== undefined)) {
      datasets.push({
        label: 'Success',
        data: trendData.map((d) => d.success || 0),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: true,
      })
    }

    if (trendData.some((d) => d.failures !== undefined)) {
      datasets.push({
        label: 'Failures',
        data: trendData.map((d) => d.failures || 0),
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true,
      })
    }

    if (trendData.some((d) => d.warnings !== undefined)) {
      datasets.push({
        label: 'Warnings',
        data: trendData.map((d) => d.warnings || 0),
        borderColor: '#F59E0B',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        tension: 0.4,
        fill: true,
      })
    }

    return { labels, datasets }
  }

  // Otherwise, assume it's already in Chart.js format
  return props.data as ChartData
})

const defaultOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
    },
  },
  scales: {
    x: {
      display: true,
      grid: {
        display: false,
      },
    },
    y: {
      display: true,
      grid: {
        color: 'rgba(0, 0, 0, 0.1)',
      },
    },
  },
  elements: {
    point: {
      radius: 4,
      hoverRadius: 6,
    },
    line: {
      tension: 0.1,
    },
  },
}

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const,
    },
    tooltip: {
      callbacks: {
        label: function (context: any) {
          const label = context.label || ''
          const value = context.parsed
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const percentage = ((value / total) * 100).toFixed(1)
          return `${label}: ${value} (${percentage}%)`
        },
      },
    },
  },
}

const createChart = async () => {
  if (!chartCanvas.value || !chartData.value) return

  // Destroy existing chart
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const baseOptions =
    props.type === 'doughnut'
      ? { ...doughnutOptions, ...props.options }
      : { ...defaultOptions, ...props.options }

  const options = {
    ...baseOptions,
    plugins: {
      ...baseOptions.plugins,
      legend: {
        ...baseOptions.plugins?.legend,
        display: props.showLegend,
      },
    },
  }

  chartInstance = new ChartJS(ctx, {
    type: props.type,
    data: chartData.value,
    options,
  })
}

const updateChart = async () => {
  if (!chartInstance || !chartData.value) return

  chartInstance.data = chartData.value
  chartInstance.update()
}

// Watch for data changes
watch(
  () => chartData.value,
  () => {
    nextTick(() => {
      if (chartInstance) {
        updateChart()
      } else {
        createChart()
      }
    })
  },
  { deep: true },
)

// Watch for type changes
watch(
  () => props.type,
  () => {
    nextTick(() => {
      createChart()
    })
  },
)

onMounted(async () => {
  await nextTick()
  createChart()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script>
