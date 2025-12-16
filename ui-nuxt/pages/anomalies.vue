<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Data Quality Anomalies</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Failing and warning clef executions (including Forecast + Drift).
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
          :loading="isRefreshing"
          @click="refresh"
        >
          Refresh
        </UButton>
      </div>
    </div>

    <UCard v-if="error">
      <div class="text-sm text-red-600 dark:text-red-400">{{ error }}</div>
    </UCard>

    <UCard v-if="showFilters">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UFormGroup label="Severity">
          <USelect v-model="filters.severity" :options="severityOptions" placeholder="All" />
        </UFormGroup>
        <UFormGroup label="Stave">
          <USelect v-model="filters.stave" :options="staveOptions" placeholder="All" />
        </UFormGroup>
        <UFormGroup label="Status">
          <USelect v-model="filters.status" :options="statusOptions" placeholder="All" />
        </UFormGroup>
        <UFormGroup label="Type">
          <USelect v-model="filters.checkType" :options="checkTypeOptions" placeholder="All" />
        </UFormGroup>
      </div>
    </UCard>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <UCard class="gradient-error text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Critical</p>
            <p class="text-3xl font-bold">{{ summary.critical }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-warning text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">High</p>
            <p class="text-3xl font-bold">{{ summary.high }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-circle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="bg-yellow-500 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Medium</p>
            <p class="text-3xl font-bold">{{ summary.medium }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="bg-blue-500 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Low</p>
            <p class="text-3xl font-bold">{{ summary.low }}</p>
          </div>
          <Icon name="i-heroicons-information-circle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>
    </div>

    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h3 class="text-lg font-semibold">Failing / Warning Check Runs</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Showing {{ filteredRows.length }} of {{ rows.length }} recent runs.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <UButton
              color="primary"
              variant="outline"
              size="sm"
              icon="i-heroicons-arrow-down-tray"
              @click="exportRows"
            >
              Export
            </UButton>
          </div>
        </div>
      </template>

      <UTable :rows="filteredRows" :columns="columns" class="w-full">
        <template #clef-data="{ row }">
          <div class="space-y-0.5">
            <div class="font-medium text-gray-900 dark:text-white">
              {{ row.clef_name || row.clef_id }}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">{{ row.check_type }}</div>
          </div>
        </template>

        <template #message-data="{ row }">
          <div class="max-w-xl truncate" :title="row.message || ''">{{ row.message || '—' }}</div>
        </template>

        <template #severity-data="{ row }">
          <UBadge :color="severityColor(row.severity)" variant="solid">
            {{ row.severity }}
          </UBadge>
        </template>

        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" variant="subtle">
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
              @click="openDetails(row)"
            />
            <UButton
              color="green"
              variant="ghost"
              size="sm"
              icon="i-heroicons-play"
              :loading="runningClefId === row.clef_id"
              @click="runNow(row.clef_id)"
            />
          </div>
        </template>
      </UTable>
    </UCard>

    <UModal v-model="showModal" :ui="{ width: 'w-full sm:max-w-4xl' }">
      <UCard v-if="selected">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Check Result Details</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showModal = false"
            />
          </div>
        </template>

        <div class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 class="font-semibold mb-2">Basic Information</h4>
              <div class="space-y-2">
                <div class="flex justify-between gap-4">
                  <span class="text-gray-600 dark:text-gray-400">Clef:</span>
                  <span class="font-medium text-right">{{
                    selected.clef_name || selected.clef_id
                  }}</span>
                </div>
                <div class="flex justify-between gap-4">
                  <span class="text-gray-600 dark:text-gray-400">Type:</span>
                  <span class="font-medium text-right">{{ selected.check_type }}</span>
                </div>
                <div class="flex justify-between gap-4">
                  <span class="text-gray-600 dark:text-gray-400">Stave:</span>
                  <span class="font-medium text-right">{{
                    selected.stave_name || selected.stave_id
                  }}</span>
                </div>
                <div class="flex justify-between gap-4">
                  <span class="text-gray-600 dark:text-gray-400">Status:</span>
                  <UBadge :color="statusColor(selected.status)" variant="subtle">{{
                    selected.status
                  }}</UBadge>
                </div>
                <div class="flex justify-between gap-4">
                  <span class="text-gray-600 dark:text-gray-400">Severity:</span>
                  <UBadge :color="severityColor(selected.severity)" variant="solid">{{
                    selected.severity
                  }}</UBadge>
                </div>
                <div class="flex justify-between gap-4">
                  <span class="text-gray-600 dark:text-gray-400">Detected:</span>
                  <span class="font-medium text-right">{{
                    formatTimeAgo(parseTimestamp(selected.timestamp))
                  }}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 class="font-semibold mb-2">Message</h4>
              <p class="text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
                {{ selected.message || '—' }}
              </p>
            </div>
          </div>

          <div>
            <h4 class="font-semibold mb-2">Metadata</h4>
            <div
              class="rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4"
            >
              <pre class="text-xs overflow-auto whitespace-pre-wrap">{{
                formatJson(selected.metadata || selected.details)
              }}</pre>
            </div>
          </div>

          <div class="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <UButton
              color="green"
              icon="i-heroicons-play"
              :loading="runningClefId === selected.clef_id"
              @click="runNow(selected.clef_id)"
            >
              Run Clef Now
            </UButton>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({
  title: 'Anomalies - DataMetronome',
})

const showFilters = ref(false)
const isRefreshing = ref(false)
const showModal = ref(false)
const selected = ref<any | null>(null)
const runningClefId = ref<string | null>(null)

const filters = ref({
  severity: '',
  stave: '',
  status: '',
  checkType: '',
})

const severityOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
]

const statusOptions = [
  { label: 'Fail', value: 'fail' },
  { label: 'Warn', value: 'warn' },
  { label: 'Pass', value: 'pass' },
]

const columns = [
  { key: 'clef', label: 'Clef' },
  { key: 'message', label: 'Message' },
  { key: 'severity', label: 'Severity' },
  { key: 'status', label: 'Status' },
  { key: 'detected', label: 'Detected' },
  { key: 'stave_name', label: 'Stave' },
  { key: 'actions', label: 'Actions' },
]

const { fetchLatestResults, checkResults, runCheck, error } = useClefs()

const rows = computed(() => {
  const raw = (checkResults.value || []) as any[]
  return raw
    .filter((r) => {
      const s = String(r?.status || '').toLowerCase()
      return s !== 'pass' && s !== 'passed'
    })
    .map((r) => ({
      ...r,
      status: String(r?.status || 'unknown').toLowerCase(),
      severity: normalizeSeverity(r?.severity),
      detected: parseTimestamp(r?.timestamp),
    }))
})

const staveOptions = computed(() => {
  const names = new Map<string, string>()
  for (const r of (checkResults.value || []) as any[]) {
    const name = r?.stave_name || r?.stave_id
    if (name) names.set(name, name)
  }
  return Array.from(names.values()).map((s) => ({ label: s, value: s }))
})

const checkTypeOptions = computed(() => {
  const types = new Set<string>()
  for (const r of (checkResults.value || []) as any[]) {
    if (r?.check_type) types.add(r.check_type)
  }
  return Array.from(types.values())
    .sort()
    .map((t) => ({ label: t, value: t }))
})

const filteredRows = computed(() => {
  return rows.value.filter((r) => {
    if (filters.value.severity && r.severity !== filters.value.severity) return false
    if (filters.value.status && r.status !== filters.value.status) return false
    if (filters.value.checkType && r.check_type !== filters.value.checkType) return false
    if (filters.value.stave) {
      const name = r?.stave_name || r?.stave_id
      if (name !== filters.value.stave) return false
    }
    return true
  })
})

const summary = computed(() => {
  const out = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const r of rows.value) {
    if (r.severity === 'critical') out.critical += 1
    else if (r.severity === 'high') out.high += 1
    else if (r.severity === 'medium') out.medium += 1
    else out.low += 1
  }
  return out
})

function parseTimestamp(ts?: string): Date {
  if (!ts) return new Date()
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? new Date() : d
}

function normalizeSeverity(severity?: string | null): string {
  const s = String(severity || '').toLowerCase()
  if (s === 'cacophony') return 'critical'
  if (s === 'dissonance') return 'high'
  if (s === 'harmony') return 'low'
  return 'medium'
}

function severityColor(sev: string) {
  return (
    (
      {
        critical: 'red',
        high: 'orange',
        medium: 'yellow',
        low: 'blue',
      } as Record<string, string>
    )[sev] || 'gray'
  )
}

function statusColor(status: string) {
  return (
    (
      {
        fail: 'red',
        failed: 'red',
        warn: 'yellow',
        warning: 'yellow',
        pass: 'green',
        passed: 'green',
      } as Record<string, string>
    )[status] || 'gray'
  )
}

function formatTimeAgo(date: Date) {
  const now = new Date()
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))

  if (diffInMinutes < 60) return `${diffInMinutes} minutes ago`
  if (diffInMinutes < 1440) {
    const hours = Math.floor(diffInMinutes / 60)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  }
  const days = Math.floor(diffInMinutes / 1440)
  return `${days} day${days > 1 ? 's' : ''} ago`
}

function formatJson(value: any) {
  if (!value) return '—'
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function openDetails(row: any) {
  selected.value = row
  showModal.value = true
}

async function runNow(clefId: string) {
  if (!clefId) return
  runningClefId.value = clefId
  try {
    await runCheck(clefId)
    await fetchLatestResults(50)
  } finally {
    runningClefId.value = null
  }
}

async function refresh() {
  isRefreshing.value = true
  try {
    await fetchLatestResults(50)
  } finally {
    isRefreshing.value = false
  }
}

function exportRows() {
  const data = filteredRows.value.map((r: any) => ({
    clef: r.clef_name || r.clef_id,
    clef_id: r.clef_id,
    check_type: r.check_type,
    status: r.status,
    severity: r.severity,
    timestamp: r.timestamp,
    stave: r.stave_name || r.stave_id,
    message: r.message,
    metadata: r.metadata || r.details,
  }))
  console.log('Export anomalies (copy from console):', data)
}

await refresh()
</script>
