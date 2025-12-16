<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Brain (Forecast + Drift)</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Live results from Tier-2 clefs: anomaly detection (forecast) and distribution drift.
        </p>
      </div>
      <div class="flex items-center gap-3">
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

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold">Forecast (Anomaly Detection)</h3>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Detects unexpected deviations based on historical time series.
              </p>
            </div>
            <UButton
              v-if="forecastLatest"
              color="green"
              icon="i-heroicons-play"
              :loading="runningClefId === forecastLatest.clef_id"
              @click="runNow(forecastLatest.clef_id)"
            >
              Run
            </UButton>
          </div>
        </template>

        <div v-if="!forecastLatest" class="text-gray-600 dark:text-gray-400">
          No forecast executions found yet.
        </div>

        <div v-else class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <div class="font-medium text-gray-900 dark:text-white">
                {{ forecastLatest.clef_name || forecastLatest.clef_id }}
              </div>
              <div class="text-sm text-gray-600 dark:text-gray-400">
                {{ forecastLatest.stave_name || forecastLatest.stave_id }} •
                {{ formatTimeAgo(parseTimestamp(forecastLatest.timestamp)) }}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <UBadge :color="statusColor(String(forecastLatest.status || ''))" variant="subtle">
                {{ String(forecastLatest.status || '').toLowerCase() }}
              </UBadge>
              <UBadge
                :color="severityColor(normalizeSeverity(forecastLatest.severity))"
                variant="solid"
              >
                {{ normalizeSeverity(forecastLatest.severity) }}
              </UBadge>
            </div>
          </div>

          <div
            class="rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4"
          >
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">Message</div>
            <div class="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
              {{ forecastLatest.message || '—' }}
            </div>
          </div>

          <div
            class="rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4"
          >
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">Metadata</div>
            <pre class="text-xs overflow-auto whitespace-pre-wrap">{{
              formatJson(forecastLatest.metadata || forecastLatest.details)
            }}</pre>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold">Drift (Distribution Shift)</h3>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Compares a current window vs baseline (e.g., KS test p-value).
              </p>
            </div>
            <UButton
              v-if="driftLatest"
              color="green"
              icon="i-heroicons-play"
              :loading="runningClefId === driftLatest.clef_id"
              @click="runNow(driftLatest.clef_id)"
            >
              Run
            </UButton>
          </div>
        </template>

        <div v-if="!driftLatest" class="text-gray-600 dark:text-gray-400">
          No drift executions found yet.
        </div>

        <div v-else class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <div class="font-medium text-gray-900 dark:text-white">
                {{ driftLatest.clef_name || driftLatest.clef_id }}
              </div>
              <div class="text-sm text-gray-600 dark:text-gray-400">
                {{ driftLatest.stave_name || driftLatest.stave_id }} •
                {{ formatTimeAgo(parseTimestamp(driftLatest.timestamp)) }}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <UBadge :color="statusColor(String(driftLatest.status || ''))" variant="subtle">
                {{ String(driftLatest.status || '').toLowerCase() }}
              </UBadge>
              <UBadge
                :color="severityColor(normalizeSeverity(driftLatest.severity))"
                variant="solid"
              >
                {{ normalizeSeverity(driftLatest.severity) }}
              </UBadge>
            </div>
          </div>

          <div
            class="rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4"
          >
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">Message</div>
            <div class="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
              {{ driftLatest.message || '—' }}
            </div>
          </div>

          <div
            class="rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4"
          >
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">Metadata</div>
            <pre class="text-xs overflow-auto whitespace-pre-wrap">{{
              formatJson(driftLatest.metadata || driftLatest.details)
            }}</pre>
          </div>
        </div>
      </UCard>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold">Forecast: observed vs bounds</h3>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Latest forecast run (Observed, Lower, Upper).
              </p>
            </div>
          </div>
        </template>

        <div v-if="!forecastBarData" class="text-gray-600 dark:text-gray-400">
          Not enough forecast metadata to chart yet. Click “Run”.
        </div>
        <div v-else class="h-[260px]">
          <TrendChart :data="forecastBarData" type="bar" :height="260" :show-legend="true" />
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold">Drift: baseline vs current mean</h3>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Latest drift run (Baseline mean vs Current mean).
              </p>
            </div>
          </div>
        </template>

        <div v-if="!driftBarData" class="text-gray-600 dark:text-gray-400">
          Not enough drift metadata to chart yet. Click “Run”.
        </div>
        <div v-else class="h-[260px]">
          <TrendChart :data="driftBarData" type="bar" :height="260" :show-legend="true" />
        </div>
      </UCard>
    </div>

    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold">Brain trend</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Forecast observed and drift signal over recent runs.
            </p>
          </div>
        </div>
      </template>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="h-[260px]">
          <div v-if="!forecastTrendData" class="text-gray-600 dark:text-gray-400">
            No forecast history yet.
          </div>
          <TrendChart
            v-else
            :data="forecastTrendData"
            type="line"
            :height="260"
            :show-legend="true"
            :options="trendLineOptions"
          />
        </div>

        <div class="h-[260px]">
          <div v-if="!driftTrendData" class="text-gray-600 dark:text-gray-400">
            No drift history yet.
          </div>
          <TrendChart
            v-else
            :data="driftTrendData"
            type="line"
            :height="260"
            :show-legend="true"
            :options="trendLineOptions"
          />
        </div>
      </div>
    </UCard>

    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold">Latest Brain Runs</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Forecast + Drift from the latest checks feed.
            </p>
          </div>
        </div>
      </template>

      <UTable :rows="brainRows" :columns="brainColumns" class="w-full">
        <template #clef-data="{ row }">
          <div class="space-y-0.5">
            <div class="font-medium text-gray-900 dark:text-white">
              {{ row.clef_name || row.clef_id }}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">{{ row.check_type }}</div>
          </div>
        </template>

        <template #status-data="{ row }">
          <UBadge :color="statusColor(String(row.status || ''))" variant="subtle">
            {{ String(row.status || '').toLowerCase() }}
          </UBadge>
        </template>

        <template #severity-data="{ row }">
          <UBadge :color="severityColor(normalizeSeverity(row.severity))" variant="solid">
            {{ normalizeSeverity(row.severity) }}
          </UBadge>
        </template>

        <template #timestamp-data="{ row }">
          {{ formatTimeAgo(parseTimestamp(row.timestamp)) }}
        </template>

        <template #actions-data="{ row }">
          <div class="flex items-center gap-2">
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({
  title: 'Brain - DataMetronome',
})

const isRefreshing = ref(false)
const runningClefId = ref<string | null>(null)

const { fetchLatestResults, checkResults, runCheck, error } = useClefs()

const brainRows = computed(() => {
  return (checkResults.value || []).filter((r: any) => {
    const t = String(r?.check_type || '')
    return t === 'forecast' || t === 'data_profile_drift' || t === 'drift'
  }) as any[]
})

function getMetadata(r: any): Record<string, any> | null {
  const raw = r?.metadata || r?.details
  if (!raw) return null
  if (typeof raw === 'object') return raw
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw)
    } catch {
      return null
    }
  }
  return null
}

function parseObservedFromMessage(msg?: string | null): number | null {
  if (!msg) return null
  const m = msg.match(/Value\\s+([0-9]+(?:\\.[0-9]+)?)/i)
  if (!m) return null
  const v = Number(m[1])
  return Number.isFinite(v) ? v : null
}

const forecastLatest = computed(() => {
  return brainRows.value.find((r: any) => String(r?.check_type || '') === 'forecast') || null
})

const driftLatest = computed(() => {
  return (
    brainRows.value.find((r: any) => String(r?.check_type || '') === 'data_profile_drift') ||
    brainRows.value.find((r: any) => String(r?.check_type || '') === 'drift') ||
    null
  )
})

const forecastBarData = computed(() => {
  const r = forecastLatest.value
  if (!r) return null
  const meta = getMetadata(r)
  const lower = Number(meta?.lower_bound)
  const upper = Number(meta?.upper_bound)
  const observed =
    Number(meta?.observed_value) ||
    Number(meta?.observed) ||
    (parseObservedFromMessage(r?.message) ?? NaN)

  if (![lower, upper, observed].every((x) => Number.isFinite(x))) return null
  return {
    labels: ['Lower', 'Observed', 'Upper'],
    datasets: [
      {
        label: 'Value',
        data: [lower, observed, upper],
        backgroundColor: [
          'rgba(107,114,128,0.35)',
          'rgba(239,68,68,0.45)',
          'rgba(107,114,128,0.35)',
        ],
        borderColor: 'rgba(107,114,128,1)',
      },
    ],
  }
})

const driftBarData = computed(() => {
  const r = driftLatest.value
  if (!r) return null
  const meta = getMetadata(r)
  const stats = meta?.stats_metadata || meta?.stats || {}
  const baselineMean = Number(stats?.baseline_mean ?? meta?.baseline_mean)
  const currentMean = Number(stats?.current_mean ?? meta?.current_mean)
  if (![baselineMean, currentMean].every((x) => Number.isFinite(x))) return null

  return {
    labels: ['Baseline mean', 'Current mean'],
    datasets: [
      {
        label: 'Mean',
        data: [baselineMean, currentMean],
        backgroundColor: ['rgba(59,130,246,0.45)', 'rgba(168,85,247,0.45)'],
        borderColor: 'rgba(59,130,246,1)',
      },
    ],
  }
})

const trendLineOptions = {
  plugins: {
    legend: { position: 'top' as const },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { grid: { display: false } },
  },
}

const forecastTrendData = computed(() => {
  const points = brainRows.value
    .filter((r: any) => String(r?.check_type || '') === 'forecast')
    .map((r: any) => {
      const meta = getMetadata(r) || {}
      const ts = parseTimestamp(r?.timestamp)
      const label = ts.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
      const observed =
        Number(meta?.observed_value) ||
        Number(meta?.observed) ||
        (parseObservedFromMessage(r?.message) ?? NaN)
      const lower = Number(meta?.lower_bound)
      const upper = Number(meta?.upper_bound)
      return { label, observed, lower, upper }
    })
    .filter((p) => p.label)
    .reverse()

  if (points.length < 1) return null

  const labels = points.map((p) => p.label)
  const observed = points.map((p) => (Number.isFinite(p.observed) ? p.observed : null))
  const lower = points.map((p) => (Number.isFinite(p.lower) ? p.lower : null))
  const upper = points.map((p) => (Number.isFinite(p.upper) ? p.upper : null))

  return {
    labels,
    datasets: [
      {
        label: 'Observed',
        data: observed as any,
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239,68,68,0.08)',
        tension: 0.2,
        fill: false,
      },
      {
        label: 'Lower bound',
        data: lower as any,
        borderColor: 'rgba(107,114,128,0.9)',
        backgroundColor: 'rgba(107,114,128,0.05)',
        tension: 0.2,
        fill: false,
      },
      {
        label: 'Upper bound',
        data: upper as any,
        borderColor: 'rgba(107,114,128,0.9)',
        backgroundColor: 'rgba(107,114,128,0.05)',
        tension: 0.2,
        fill: false,
      },
    ],
  }
})

const driftTrendData = computed(() => {
  const points = brainRows.value
    .filter((r: any) => {
      const t = String(r?.check_type || '')
      return t === 'data_profile_drift' || t === 'drift'
    })
    .map((r: any) => {
      const meta = getMetadata(r) || {}
      const ts = parseTimestamp(r?.timestamp)
      const label = ts.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
      const p = Number(meta?.p_value ?? meta?.pvalue ?? meta?.p)
      const signal = Number.isFinite(p) && p > 0 ? -Math.log10(p) : null
      return { label, signal }
    })
    .filter((p) => p.label)
    .reverse()

  if (points.length < 1) return null

  return {
    labels: points.map((p) => p.label),
    datasets: [
      {
        label: '-log10(p-value)',
        data: points.map((p) => p.signal) as any,
        borderColor: '#8B5CF6',
        backgroundColor: 'rgba(168,85,247,0.08)',
        tension: 0.2,
        fill: false,
      },
    ],
  }
})

const brainColumns = [
  { key: 'clef', label: 'Clef' },
  { key: 'message', label: 'Message' },
  { key: 'status', label: 'Status' },
  { key: 'severity', label: 'Severity' },
  { key: 'timestamp', label: 'When' },
  { key: 'stave_name', label: 'Stave' },
  { key: 'actions', label: 'Run' },
]

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
  const s = String(status || '').toLowerCase()
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
    )[s] || 'gray'
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

await refresh()
</script>
