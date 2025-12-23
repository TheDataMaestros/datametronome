<template>
  <div class="space-y-6">
    <!-- Welcome Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Welcome back</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Here's what's happening with your data quality monitoring system.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <UButton
          color="primary"
          variant="outline"
          icon="i-heroicons-arrow-down-tray"
          @click="exportDashboard"
        >
          Export Data
        </UButton>
        <UButton
          color="primary"
          icon="i-heroicons-play"
          @click="runAllChecks"
          :loading="isRunningChecks"
        >
          Run All Checks
        </UButton>
      </div>
    </div>

    <!-- System Health Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <UCard class="gradient-primary text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Success Rate</p>
            <p class="text-3xl font-bold">{{ systemMetrics.successRate }}%</p>
            <p class="text-sm opacity-90">
              {{ systemMetrics.successRateChange > 0 ? '+' : ''
              }}{{ systemMetrics.successRateChange }}% from yesterday
            </p>
          </div>
          <Icon name="i-heroicons-check-circle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-success text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Active Sources</p>
            <p class="text-3xl font-bold">{{ systemMetrics.activeSources }}</p>
            <p class="text-sm opacity-90">{{ systemMetrics.totalSources }} total configured</p>
          </div>
          <Icon name="i-heroicons-server" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-warning text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Quality Checks</p>
            <p class="text-3xl font-bold">{{ systemMetrics.activeChecks }}</p>
            <p class="text-sm opacity-90">{{ systemMetrics.scheduledChecks }} scheduled</p>
          </div>
          <Icon name="i-heroicons-check-circle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-error text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Anomalies</p>
            <p class="text-3xl font-bold">{{ systemMetrics.anomalies }}</p>
            <p class="text-sm opacity-90">Last 24 hours</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- System Health Chart -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">System Health Trend</h3>
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="refreshHealthChart"
            />
          </div>
        </template>
        <div class="h-64 flex items-center justify-center">
          <div class="text-center">
            <Icon name="i-heroicons-chart-bar" class="w-12 h-12 mx-auto text-gray-400 mb-2" />
            <p class="text-gray-500">Interactive chart coming soon</p>
            <p class="text-sm text-gray-400 mt-1">Success Rate: {{ systemMetrics.successRate }}%</p>
          </div>
        </div>
      </UCard>

      <!-- Anomaly Distribution -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Anomaly Distribution</h3>
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="refreshAnomalyChart"
            />
          </div>
        </template>
        <div class="h-64 flex items-center justify-center">
          <div class="text-center">
            <Icon name="i-heroicons-chart-pie" class="w-12 h-12 mx-auto text-gray-400 mb-2" />
            <p class="text-gray-500">Distribution chart coming soon</p>
            <div class="mt-4 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-sm">Passed:</span>
                <span class="font-medium text-green-600">
                  {{ dashboardMetrics?.distribution?.passed ?? 0 }}%
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm">Failed:</span>
                <span class="font-medium text-red-600">
                  {{ dashboardMetrics?.distribution?.failed ?? 0 }}%
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm">Warning:</span>
                <span class="font-medium text-yellow-600">
                  {{ dashboardMetrics?.distribution?.warning ?? 0 }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Recent Activity & Quick Actions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Activity -->
      <UCard class="lg:col-span-2">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Recent Activity</h3>
            <UButton color="primary" variant="ghost" size="sm" @click="navigateTo('/anomalies')">
              View All
            </UButton>
          </div>
        </template>
        <div class="space-y-4">
          <div
            v-for="activity in recentActivity"
            :key="activity.id"
            class="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <div class="flex-shrink-0">
              <UAvatar
                :color="getStatusColor(activity.status)"
                size="sm"
                :icon="getStatusIcon(activity.status)"
              />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white">
                {{ activity.description }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ activity.source }} • {{ formatTimeAgo(activity.timestamp) }}
              </p>
            </div>
            <div class="flex-shrink-0">
              <UBadge :color="getStatusColor(activity.status)" variant="subtle" size="sm">
                {{ activity.statusLabel }}
              </UBadge>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Quick Actions -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Quick Actions</h3>
        </template>
        <div class="space-y-3">
          <UButton
            color="primary"
            variant="outline"
            block
            icon="i-heroicons-plus"
            @click="navigateTo('/staves')"
          >
            Add Data Source
          </UButton>
          <UButton
            color="green"
            variant="outline"
            block
            icon="i-heroicons-check-circle"
            @click="navigateTo('/clefs')"
          >
            Create Quality Check
          </UButton>
          <UButton
            color="blue"
            variant="outline"
            block
            icon="i-heroicons-document-text"
            @click="navigateTo('/reports')"
          >
            Generate Report
          </UButton>
          <UButton
            color="purple"
            variant="outline"
            block
            icon="i-heroicons-magnifying-glass"
            @click="navigateTo('/investigation')"
          >
            Investigate Data
          </UButton>
        </div>
      </UCard>
    </div>

    <!-- Data Source Status -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Data Source Status</h3>
          <UButton color="primary" variant="ghost" size="sm" @click="navigateTo('/staves')">
            Manage Sources
          </UButton>
        </div>
      </template>
      <UTable :rows="dataSources" :columns="dataSourceColumns" class="w-full">
        <template #status-data="{ row }">
          <UBadge :color="getStatusColor(row.status)" variant="subtle">
            {{ row.status }}
          </UBadge>
        </template>
        <template #last-check-data="{ row }">
          {{ formatTimeAgo(row.lastCheck) }}
        </template>
        <template #actions-data="{ row }">
          <div class="flex items-center gap-2">
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="testConnection(row.id)"
            />
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-eye"
              @click="previewData(row.id)"
            />
          </div>
        </template>
      </UTable>
    </UCard>
  </div>
</template>

<script setup lang="ts">
// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

const { staves, isLoading: stavesLoading, fetchStaves } = useStaves()
const { checks, fetchLatest } = useChecks()
const { metrics: dashboardMetrics, fetchMetrics } = useDashboard()

const isRunningChecks = ref(false)

// System metrics computed from real data
const systemMetrics = computed(() => {
  if (!dashboardMetrics.value) {
    return {
      successRate: 0,
      successRateChange: 0,
      activeSources: 0,
      totalSources: 0,
      activeChecks: 0,
      scheduledChecks: 0,
      anomalies: 0,
    }
  }
  return {
    successRate: dashboardMetrics.value.success_rate,
    successRateChange: dashboardMetrics.value.success_rate_change,
    activeSources: dashboardMetrics.value.active_sources,
    totalSources: dashboardMetrics.value.total_sources,
    activeChecks: dashboardMetrics.value.active_checks,
    scheduledChecks: dashboardMetrics.value.scheduled_checks,
    anomalies: dashboardMetrics.value.anomalies,
  }
})

// Recent activity from latest checks
const recentActivity = computed(() => {
  return checks.value.slice(0, 10).map((check) => {
    const normalizedStatus = normalizeActivityStatus(check.status)
    const source = check.clef_name
      ? `${check.clef_name}${check.stave_name ? ` • ${check.stave_name}` : ''}`
      : `Clef ${check.clef_id}`
    return {
      id: check.id,
      description:
        check.message ||
        `${humanizeCheckType(check.check_type)} check ${formatStatusLabel(check.status)}`,
      source,
      status: normalizedStatus,
      statusLabel: formatStatusLabel(check.status),
      timestamp: check.timestamp,
    }
  })
})

// Transform staves data for display
const dataSources = computed(() => {
  return staves.value.map((stave) => {
    // Count checks for this stave from the checks we have
    const staveChecks = checks.value.filter((check) => check.stave_id === stave.id)
    return {
      id: stave.id,
      name: stave.name,
      type: stave.data_source_type.toUpperCase(),
      status: stave.is_active ? 'healthy' : 'warning',
      lastCheck: new Date(stave.updated_at),
      checks: staveChecks.length,
    }
  })
})

const dataSourceColumns = [
  { key: 'name', label: 'Name' },
  { key: 'type', label: 'Type' },
  { key: 'status', label: 'Status' },
  { key: 'lastCheck', label: 'Last Check' },
  { key: 'checks', label: 'Checks' },
  { key: 'actions', label: 'Actions' },
]

// Helper functions
function normalizeActivityStatus(status?: string) {
  const normalized = status?.toLowerCase()
  if (normalized === 'pass' || normalized === 'passed' || normalized === 'success') return 'success'
  if (normalized === 'warn' || normalized === 'warning') return 'warning'
  if (normalized === 'fail' || normalized === 'failed' || normalized === 'error') return 'error'
  return status ?? 'unknown'
}

function getStatusColor(status: string) {
  const normalized = normalizeActivityStatus(status)
  const colors: Record<string, string> = {
    success: 'green',
    healthy: 'green',
    warning: 'yellow',
    error: 'red',
    failed: 'red',
  }
  return colors[normalized] || 'gray'
}

function getStatusIcon(status: string) {
  const normalized = normalizeActivityStatus(status)
  const icons: Record<string, string> = {
    success: 'i-heroicons-check-circle',
    healthy: 'i-heroicons-check-circle',
    warning: 'i-heroicons-exclamation-triangle',
    error: 'i-heroicons-x-circle',
    failed: 'i-heroicons-x-circle',
  }
  return icons[normalized] || 'i-heroicons-question-mark-circle'
}

function formatTimeAgo(dateInput: Date | string) {
  const date = dateInput instanceof Date ? dateInput : new Date(dateInput)
  if (Number.isNaN(date.getTime())) {
    return 'Unknown'
  }
  const now = new Date()
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))

  if (diffInMinutes < 60) {
    return `${diffInMinutes} minutes ago`
  } else if (diffInMinutes < 1440) {
    const hours = Math.floor(diffInMinutes / 60)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  } else {
    const days = Math.floor(diffInMinutes / 1440)
    return `${days} day${days > 1 ? 's' : ''} ago`
  }
}

function formatStatusLabel(status?: string) {
  if (!status) return 'Unknown'
  const normalized = status.toLowerCase()
  if (normalized === 'pass' || normalized === 'passed' || normalized === 'success') return 'Passed'
  if (normalized === 'warn' || normalized === 'warning') return 'Warning'
  if (normalized === 'fail' || normalized === 'failed' || normalized === 'error') return 'Failed'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function humanizeCheckType(checkType?: string) {
  if (!checkType) return 'Data quality'
  return checkType
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

// Actions
async function runAllChecks() {
  isRunningChecks.value = true
  try {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000))
    // Refresh data
    await refreshData()
  } finally {
    isRunningChecks.value = false
  }
}

async function refreshData() {
  // Refresh all dashboard data
  await Promise.all([
    refreshHealthChart(),
    refreshAnomalyChart(),
    fetchStaves(),
    fetchLatest(20),
    fetchMetrics(),
  ])
}

async function refreshHealthChart() {
  // Simulate API call to refresh health chart data
  await new Promise((resolve) => setTimeout(resolve, 500))
}

async function refreshAnomalyChart() {
  // Simulate API call to refresh anomaly chart data
  await new Promise((resolve) => setTimeout(resolve, 500))
}

function exportDashboard() {
  // Implement export functionality
  console.log('Exporting dashboard data...')
}

function testConnection(sourceId: number) {
  console.log(`Testing connection for source ${sourceId}`)
}

function previewData(sourceId: number) {
  console.log(`Previewing data for source ${sourceId}`)
}

// Set page meta
useHead({
  title: 'Dashboard - DataMetronome',
})

// Load initial data
onMounted(() => {
  fetchStaves()
  fetchLatest(20)
  fetchMetrics()
})
</script>
