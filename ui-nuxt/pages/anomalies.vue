<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
          Data Quality Anomalies
        </h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Monitor and investigate data quality issues across your data sources.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <UButton
          color="primary"
          variant="outline"
          icon="i-heroicons-funnel"
          @click="showFilters = !showFilters"
        >
          Filters
        </UButton>
        <UButton
          color="primary"
          icon="i-heroicons-arrow-path"
          @click="refreshAnomalies"
          :loading="isRefreshing"
        >
          Refresh
        </UButton>
      </div>
    </div>

    <!-- Filters -->
    <UCard v-if="showFilters">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UFormGroup label="Severity">
          <USelect
            v-model="filters.severity"
            :options="severityOptions"
            placeholder="All severities"
          />
        </UFormGroup>
        <UFormGroup label="Source">
          <USelect
            v-model="filters.source"
            :options="sourceOptions"
            placeholder="All sources"
          />
        </UFormGroup>
        <UFormGroup label="Status">
          <USelect
            v-model="filters.status"
            :options="statusOptions"
            placeholder="All statuses"
          />
        </UFormGroup>
        <UFormGroup label="Date Range">
          <USelect
            v-model="filters.dateRange"
            :options="dateRangeOptions"
            placeholder="All time"
          />
        </UFormGroup>
      </div>
    </UCard>

    <!-- Anomaly Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <UCard class="gradient-error text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Critical</p>
            <p class="text-3xl font-bold">{{ anomalySummary.critical }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-warning text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">High</p>
            <p class="text-3xl font-bold">{{ anomalySummary.high }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-circle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="bg-yellow-500 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Medium</p>
            <p class="text-3xl font-bold">{{ anomalySummary.medium }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="bg-blue-500 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Low</p>
            <p class="text-3xl font-bold">{{ anomalySummary.low }}</p>
          </div>
          <Icon name="i-heroicons-information-circle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>
    </div>

    <!-- Anomalies Table -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Anomaly Details</h3>
          <div class="flex items-center gap-2">
            <UButton
              color="green"
              variant="outline"
              size="sm"
              icon="i-heroicons-check"
              @click="resolveAllAnomalies"
            >
              Resolve All
            </UButton>
            <UButton
              color="primary"
              variant="outline"
              size="sm"
              icon="i-heroicons-arrow-down-tray"
              @click="exportAnomalies"
            >
              Export
            </UButton>
          </div>
        </div>
      </template>

      <UTable
        :rows="filteredAnomalies"
        :columns="anomalyColumns"
        class="w-full"
      >
        <template #severity-data="{ row }">
          <UBadge
            :color="getSeverityColor(row.severity)"
            variant="solid"
          >
            {{ row.severity }}
          </UBadge>
        </template>

        <template #status-data="{ row }">
          <UBadge
            :color="getStatusColor(row.status)"
            variant="subtle"
          >
            {{ row.status }}
          </UBadge>
        </template>

        <template #detected-data="{ row }">
          {{ formatTimeAgo(row.detected) }}
        </template>

        <template #actions-data="{ row }">
          <div class="flex items-center gap-2">
            <UButton
              color="blue"
              variant="ghost"
              size="sm"
              icon="i-heroicons-eye"
              @click="viewAnomalyDetails(row)"
            />
            <UButton
              color="green"
              variant="ghost"
              size="sm"
              icon="i-heroicons-check"
              @click="resolveAnomaly(row.id)"
            />
            <UButton
              color="red"
              variant="ghost"
              size="sm"
              icon="i-heroicons-trash"
              @click="dismissAnomaly(row.id)"
            />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Anomaly Details Modal -->
    <UModal v-model="showAnomalyModal" :ui="{ width: 'w-full sm:max-w-4xl' }">
      <UCard v-if="selectedAnomaly">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Anomaly Details</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showAnomalyModal = false"
            />
          </div>
        </template>

        <div class="space-y-6">
          <!-- Basic Info -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 class="font-semibold mb-2">Basic Information</h4>
              <div class="space-y-2">
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Table:</span>
                  <span class="font-medium">{{ selectedAnomaly.table }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Column:</span>
                  <span class="font-medium">{{ selectedAnomaly.column }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Severity:</span>
                  <UBadge :color="getSeverityColor(selectedAnomaly.severity)" variant="solid">
                    {{ selectedAnomaly.severity }}
                  </UBadge>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Detected:</span>
                  <span class="font-medium">{{ formatTimeAgo(selectedAnomaly.detected) }}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 class="font-semibold mb-2">Impact Analysis</h4>
              <div class="space-y-2">
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Affected Records:</span>
                  <span class="font-medium">{{ selectedAnomaly.affectedRecords }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Data Quality Impact:</span>
                  <span class="font-medium">{{ selectedAnomaly.qualityImpact }}%</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Business Impact:</span>
                  <span class="font-medium">{{ selectedAnomaly.businessImpact }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div>
            <h4 class="font-semibold mb-2">Description</h4>
            <p class="text-gray-600 dark:text-gray-400">{{ selectedAnomaly.description }}</p>
          </div>

          <!-- Recommended Actions -->
          <div>
            <h4 class="font-semibold mb-2">Recommended Actions</h4>
            <div class="space-y-2">
              <div
                v-for="action in selectedAnomaly.recommendedActions"
                :key="action"
                class="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <Icon name="i-heroicons-light-bulb" class="w-4 h-4 text-yellow-500" />
                <span class="text-sm">{{ action }}</span>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <UButton
              color="green"
              icon="i-heroicons-check"
              @click="resolveAnomaly(selectedAnomaly.id)"
            >
              Resolve Anomaly
            </UButton>
            <UButton
              color="blue"
              variant="outline"
              icon="i-heroicons-arrow-path"
              @click="investigateAnomaly(selectedAnomaly.id)"
            >
              Investigate Further
            </UButton>
            <UButton
              color="red"
              variant="outline"
              icon="i-heroicons-trash"
              @click="dismissAnomaly(selectedAnomaly.id)"
            >
              Dismiss
            </UButton>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})
const showFilters = ref(false)
const isRefreshing = ref(false)
const showAnomalyModal = ref(false)
const selectedAnomaly = ref(null)

// Filters
const filters = ref({
  severity: '',
  source: '',
  status: '',
  dateRange: ''
})

const severityOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' }
]

const sourceOptions = [
  { label: 'Production Database', value: 'production' },
  { label: 'Analytics Database', value: 'analytics' },
  { label: 'Cache Database', value: 'cache' }
]

const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Investigating', value: 'investigating' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Dismissed', value: 'dismissed' }
]

const dateRangeOptions = [
  { label: 'Last 24 hours', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'All time', value: 'all' }
]

// Anomaly summary
const anomalySummary = ref({
  critical: 3,
  high: 7,
  medium: 12,
  low: 8
})

// Anomalies data
const anomalies = ref([
  {
    id: 1,
    table: 'users',
    column: 'age',
    issue: 'Age outlier detected',
    severity: 'critical',
    status: 'open',
    detected: new Date(Date.now() - 2 * 60 * 60 * 1000),
    source: 'Production Database',
    affectedRecords: 15,
    qualityImpact: 2.3,
    businessImpact: 'High',
    description: 'Detected 15 records with age values outside the expected range (18-100). These outliers may indicate data entry errors or system issues.',
    recommendedActions: [
      'Review data entry processes for age validation',
      'Check for system bugs in age calculation',
      'Implement additional validation rules'
    ]
  },
  {
    id: 2,
    table: 'orders',
    column: 'amount',
    issue: 'Amount spike detected',
    severity: 'high',
    status: 'investigating',
    detected: new Date(Date.now() - 1 * 60 * 60 * 1000),
    source: 'Production Database',
    affectedRecords: 8,
    qualityImpact: 1.8,
    businessImpact: 'Medium',
    description: 'Detected unusual spike in order amounts, with 8 orders exceeding normal thresholds. This could indicate fraudulent activity or pricing errors.',
    recommendedActions: [
      'Investigate recent pricing changes',
      'Review fraud detection systems',
      'Contact affected customers for verification'
    ]
  },
  {
    id: 3,
    table: 'events',
    column: 'timestamp',
    issue: 'Timestamp inconsistency',
    severity: 'medium',
    status: 'open',
    detected: new Date(Date.now() - 3 * 60 * 60 * 1000),
    source: 'Analytics Database',
    affectedRecords: 45,
    qualityImpact: 0.9,
    businessImpact: 'Low',
    description: 'Found 45 events with timestamps that appear to be in the future or significantly inconsistent with expected patterns.',
    recommendedActions: [
      'Check system clock synchronization',
      'Review event generation logic',
      'Implement timestamp validation'
    ]
  }
])

const anomalyColumns = [
  { key: 'table', label: 'Table' },
  { key: 'column', label: 'Column' },
  { key: 'issue', label: 'Issue' },
  { key: 'severity', label: 'Severity' },
  { key: 'status', label: 'Status' },
  { key: 'detected', label: 'Detected' },
  { key: 'source', label: 'Source' },
  { key: 'actions', label: 'Actions' }
]

// Computed
const filteredAnomalies = computed(() => {
  let filtered = anomalies.value

  if (filters.value.severity) {
    filtered = filtered.filter(a => a.severity === filters.value.severity)
  }
  if (filters.value.source) {
    filtered = filtered.filter(a => a.source.toLowerCase().includes(filters.value.source.toLowerCase()))
  }
  if (filters.value.status) {
    filtered = filtered.filter(a => a.status === filters.value.status)
  }

  return filtered
})

// Helper functions
function getSeverityColor(severity: string) {
  const colors: Record<string, string> = {
    critical: 'red',
    high: 'orange',
    medium: 'yellow',
    low: 'blue'
  }
  return colors[severity] || 'gray'
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    open: 'red',
    investigating: 'yellow',
    resolved: 'green',
    dismissed: 'gray'
  }
  return colors[status] || 'gray'
}

function formatTimeAgo(date: Date) {
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

// Actions
async function refreshAnomalies() {
  isRefreshing.value = true
  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    // Refresh data
  } finally {
    isRefreshing.value = false
  }
}

function viewAnomalyDetails(anomaly: any) {
  selectedAnomaly.value = anomaly
  showAnomalyModal.value = true
}

function resolveAnomaly(anomalyId: number) {
  const anomaly = anomalies.value.find(a => a.id === anomalyId)
  if (anomaly) {
    anomaly.status = 'resolved'
  }
  showAnomalyModal.value = false
}

function dismissAnomaly(anomalyId: number) {
  const anomaly = anomalies.value.find(a => a.id === anomalyId)
  if (anomaly) {
    anomaly.status = 'dismissed'
  }
  showAnomalyModal.value = false
}

function resolveAllAnomalies() {
  anomalies.value.forEach(anomaly => {
    if (anomaly.status === 'open') {
      anomaly.status = 'resolved'
    }
  })
}

function exportAnomalies() {
  console.log('Exporting anomalies...')
}

function investigateAnomaly(anomalyId: number) {
  console.log(`Investigating anomaly ${anomalyId}`)
  // Navigate to investigation page with anomaly context
}

// Set page meta
useHead({
  title: 'Anomalies - DataMetronome'
})
</script>
