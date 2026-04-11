<template>
  <div class="space-y-6">
    <!-- Persistent Datasource Bar -->
    <div class="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-sm">
      <DatasourceSelector
        :model-value="selectedStaveId"
        :staves="staves"
        :stave-health-scores="staveHealthScores"
        @update:model-value="selectStave"
      />
      <div v-if="selectedStaveId" class="ml-auto flex items-center gap-2 text-xs text-blue-300">
        <Icon name="i-heroicons-funnel" class="w-3 h-3" />
        <span>
          <strong>{{ staves.find(s => s.id === selectedStaveId)?.name }}</strong>
          <span v-if="scopedProfile?.domain_type"> · {{ scopedProfile.domain_type }}</span>
          <span v-if="scopedDashboard?.health_score"> · {{ scopedDashboard.health_score }}/100</span>
        </span>
        <button class="ml-1 text-blue-400 hover:text-blue-200 transition-colors" @click="selectStave(null)">✕</button>
      </div>
    </div>

    <!-- Welcome Header -->
    <div class="flex items-center justify-between">
      <div>
        <p class="dm-label mb-2">Overview</p>
        <h1
          style="font-family: var(--dm-font-display); font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
        >
          Welcome back
        </h1>
        <p class="mt-2 text-sm" style="color: var(--dm-text-secondary);">
          Here's what's happening with your data quality monitoring system.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <UButton
          color="gray"
          variant="ghost"
          icon="i-heroicons-arrow-down-tray"
          @click="exportDashboard"
        >
          Export
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
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <UCard class="gradient-primary text-white">
        <div class="flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="dm-label mb-2">Success Rate</p>
            <p class="dm-stat-value">{{ systemMetrics.successRate }}<span class="text-lg opacity-70">%</span></p>
            <p class="text-xs mt-1.5 opacity-70">
              {{ systemMetrics.successRateChange > 0 ? '+' : ''
              }}{{ systemMetrics.successRateChange }}% vs yesterday
            </p>
          </div>
          <Icon name="i-heroicons-check-circle" class="w-7 h-7 opacity-50 flex-shrink-0" />
        </div>
      </UCard>

      <UCard class="gradient-success text-white">
        <div class="flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="dm-label mb-2">Active Sources</p>
            <p class="dm-stat-value">{{ systemMetrics.activeSources }}</p>
            <p class="text-xs mt-1.5 opacity-70">{{ systemMetrics.totalSources }} total configured</p>
          </div>
          <Icon name="i-heroicons-server" class="w-7 h-7 opacity-50 flex-shrink-0" />
        </div>
      </UCard>

      <UCard class="gradient-warning text-white">
        <div class="flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="dm-label mb-2">Quality Checks</p>
            <p class="dm-stat-value">{{ systemMetrics.activeChecks }}</p>
            <p class="text-xs mt-1.5 opacity-70">{{ systemMetrics.scheduledChecks }} scheduled</p>
          </div>
          <Icon name="i-heroicons-check-circle" class="w-7 h-7 opacity-50 flex-shrink-0" />
        </div>
      </UCard>

      <UCard class="gradient-error text-white">
        <div class="flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="dm-label mb-2">Anomalies</p>
            <p class="dm-stat-value">{{ systemMetrics.anomalies }}</p>
            <p class="text-xs mt-1.5 opacity-70">Last 24 hours</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-7 h-7 opacity-50 flex-shrink-0" />
        </div>
      </UCard>
    </div>

    <!-- Intelligence Pulse Section -->
    <div v-if="intelligence && intelligence.totalReports > 0" class="space-y-3">
      <div class="flex items-center gap-3">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white tracking-tight">
          Intelligence Pulse
        </h2>
        <span class="intelligence-domain-badge">
          <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          AI Active
        </span>
        <UButton
          color="gray"
          variant="ghost"
          size="sm"
          icon="i-heroicons-chat-bubble-left-right"
          class="ml-auto"
          @click="navigateTo('/chat')"
        >
          Ask AI
        </UButton>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Health Score Gauge -->
        <div
          class="intelligence-panel rounded-xl p-5 flex flex-col items-center justify-center gap-2"
        >
          <p class="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
            Data Health
          </p>
          <div class="relative">
            <svg width="130" height="130" viewBox="0 0 100 100" aria-label="Health score gauge">
              <!-- Track arc (270° = 75% of circumference, r=42, C≈264) -->
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="rgba(148, 163, 184, 0.15)"
                stroke-width="7"
                stroke-dasharray="198 264"
                stroke-linecap="round"
                transform="rotate(-135 50 50)"
              />
              <!-- Score arc -->
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                :stroke="activeArcColor"
                stroke-width="7"
                stroke-linecap="round"
                stroke-dasharray="198 264"
                :stroke-dashoffset="198 - activeArcLength"
                transform="rotate(-135 50 50)"
                class="health-arc-fill"
              />
              <text
                x="50"
                y="48"
                text-anchor="middle"
                fill="white"
                font-size="22"
                font-weight="700"
                font-family="ui-monospace, monospace"
              >
                {{ Math.round(activeHealthScore) }}
              </text>
              <text
                x="50"
                y="62"
                text-anchor="middle"
                fill="rgba(148, 163, 184, 0.6)"
                font-size="8.5"
              >
                / 100
              </text>
            </svg>
          </div>
          <div class="text-center">
            <p
              class="text-sm font-semibold"
              :class="{
                'text-emerald-400': activeHealthScore >= 80,
                'text-amber-400':
                  activeHealthScore >= 50 && activeHealthScore < 80,
                'text-red-400': activeHealthScore < 50,
              }"
            >
              {{
                activeHealthScore >= 80
                  ? 'Strong'
                  : activeHealthScore >= 50
                    ? 'Moderate'
                    : 'Needs Attention'
              }}
            </p>
            <p class="text-xs text-slate-500 mt-0.5">
              {{ intelligence.totalReports }}
              {{ intelligence.totalReports !== 1 ? 'reports' : 'report' }} generated
            </p>
          </div>
        </div>

        <!-- Source Coverage -->
        <div class="intelligence-panel rounded-xl p-5 flex flex-col justify-between">
          <p class="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">
            Source Coverage
          </p>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between items-baseline mb-2">
                <span class="text-3xl font-bold text-white">{{
                  intelligence.profiledSources
                }}</span>
                <span class="text-sm text-slate-400">of {{ systemMetrics.activeSources }} active</span>
              </div>
              <div class="h-2 rounded-full bg-slate-700 overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-1000 ease-out"
                  :style="{
                    width: `${intelligence.profiledRatio}%`,
                    background: 'linear-gradient(90deg, #3b82f6, #06b6d4)',
                  }"
                />
              </div>
              <p class="text-xs text-slate-500 mt-1">{{ intelligence.profiledRatio }}% profiled</p>
            </div>

            <!-- Top table metrics as business KPIs -->
            <div v-if="Object.keys(intelligence.tableMetrics).length" class="space-y-1">
              <div
                v-for="(count, table) in topTableMetrics"
                :key="table"
                class="flex justify-between items-center text-xs"
              >
                <span class="text-slate-500 capitalize">{{ formatTableName(String(table)) }}</span>
                <span class="text-slate-300 font-medium tabular-nums">{{ count.toLocaleString() }}</span>
              </div>
            </div>

            <button
              class="w-full flex items-center gap-3 pt-3 border-t border-slate-700/50 hover:opacity-80 transition-opacity text-left"
              @click="navigateTo('/insights')"
            >
              <div
                class="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0"
              >
                <Icon name="i-heroicons-chart-bar-square" class="w-4 h-4 text-blue-400" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-white">
                  {{ intelligence.totalReports }} Analysis Reports
                </p>
                <p class="text-xs text-slate-500">View AI findings →</p>
              </div>
            </button>
          </div>
        </div>

        <!-- Action Items -->
        <div class="intelligence-panel rounded-xl p-5 flex flex-col gap-3 overflow-hidden">
          <div class="flex items-baseline justify-between">
            <p class="text-xs font-semibold uppercase tracking-widest text-slate-400">Action Items</p>
            <p v-if="intelligence.lastAnalyzedAt" class="text-[11px] text-slate-500">
              Data as of {{ formatAnalyzedAt(intelligence.lastAnalyzedAt) }}
            </p>
          </div>

          <!-- Suggestions -->
          <template v-if="activeSuggestions.length > 0">
            <div
              v-for="(sug, i) in activeSuggestions"
              :key="'sug-' + i"
              class="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 space-y-2"
            >
              <div class="flex items-start gap-2">
                <span
                  class="flex-shrink-0 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded mt-0.5"
                  :class="sug.priority === 'high' ? 'bg-red-500/30 text-red-300' : 'bg-amber-500/20 text-amber-400'"
                >{{ sug.priority }}</span>
                <span v-if="sug.stave_name" class="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400 font-mono">
                  {{ sug.stave_name }}
                </span>
                <p class="text-xs font-medium text-amber-200 leading-snug line-clamp-2">{{ sug.action }}</p>
              </div>
              <div class="flex gap-2 pt-1">
                <UButton size="xs" color="amber" variant="soft" icon="i-heroicons-magnifying-glass" @click.stop="navigateTo('/insights')">
                  Investigate
                </UButton>
                <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-arrow-right" @click.stop="navigateTo('/insights')">
                  Full Report
                </UButton>
              </div>
            </div>
          </template>
          <button
            v-else-if="intelligence.pendingSuggestions > 0"
            class="w-full flex items-center justify-between p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
            @click="navigateTo('/insights')"
          >
            <div class="flex items-center gap-2">
              <Icon name="i-heroicons-light-bulb" class="w-4 h-4 text-amber-400" />
              <span class="text-sm text-amber-300 font-medium">{{ intelligence.pendingSuggestions }} Suggestion{{ intelligence.pendingSuggestions !== 1 ? 's' : '' }}</span>
            </div>
            <Icon name="i-heroicons-arrow-right" class="w-4 h-4 text-amber-400" />
          </button>

          <!-- Anomalies -->
          <template v-if="activeAnomalies.length > 0">
            <div
              v-for="(ano, i) in activeAnomalies"
              :key="'ano-' + i"
              class="p-3 rounded-lg bg-red-500/10 border border-red-500/20 space-y-2"
            >
              <div class="flex items-start gap-2">
                <span class="flex-shrink-0 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-500/30 text-red-300 mt-0.5">
                  {{ ano.severity }}
                </span>
                <span v-if="ano.stave_name" class="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400 font-mono mt-0.5">
                  {{ ano.stave_name }}
                </span>
                <div class="min-w-0 flex-1">
                  <p class="text-xs font-medium text-red-200 leading-snug line-clamp-2">{{ ano.description }}</p>
                  <p v-if="ano.table" class="text-[11px] text-slate-500 mt-0.5">table: <code class="text-slate-400">{{ ano.table }}</code></p>
                  <!-- Timestamps -->
                  <div class="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
                    <span v-if="ano.detected_at" class="flex items-center gap-1 text-[10px] text-slate-500">
                      <Icon name="i-heroicons-magnifying-glass" class="w-2.5 h-2.5" />
                      Detected {{ formatAnomalyTime(ano.detected_at) }}
                    </span>
                    <span v-if="ano.snapshot_at" class="flex items-center gap-1 text-[10px] text-slate-500">
                      <Icon name="i-heroicons-camera" class="w-2.5 h-2.5" />
                      Snapshot {{ formatAnomalyTime(ano.snapshot_at) }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="flex gap-2 pt-1">
                <UButton size="xs" color="red" variant="soft" icon="i-heroicons-magnifying-glass" @click.stop="navigateTo('/insights')">
                  Investigate
                </UButton>
                <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-arrow-path" @click.stop="triggerReanalyze">
                  Re-analyze
                </UButton>
              </div>
            </div>
          </template>
          <button
            v-else-if="intelligence.criticalAnomalies > 0"
            class="w-full flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 transition-colors"
            @click="navigateTo('/insights')"
          >
            <div class="flex items-center gap-2">
              <Icon name="i-heroicons-exclamation-triangle" class="w-4 h-4 text-red-400" />
              <span class="text-sm text-red-300 font-medium">{{ intelligence.criticalAnomalies }} Critical Anomal{{ intelligence.criticalAnomalies !== 1 ? 'ies' : 'y' }}</span>
            </div>
            <Icon name="i-heroicons-arrow-right" class="w-4 h-4 text-red-400" />
          </button>

          <!-- All clear -->
          <div
            v-else-if="intelligence.pendingSuggestions === 0 && intelligence.criticalAnomalies === 0"
            class="flex items-center gap-2 p-3 rounded-lg bg-slate-700/30 border border-slate-600/20"
          >
            <Icon name="i-heroicons-check-circle" class="w-4 h-4 text-emerald-400" />
            <span class="text-sm text-slate-400">No Critical Issues</span>
          </div>

          <UButton
            color="primary"
            variant="soft"
            block
            size="sm"
            icon="i-heroicons-sparkles"
            @click="navigateTo('/insights')"
          >
            View All Insights
          </UButton>
        </div>
      </div>
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
            <UButton color="primary" variant="ghost" size="sm" @click="navigateTo('/insights')">
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
            @click="navigateTo('/insights')"
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

const { loadPrefs } = useDashboardPrefs()
const { selectedStaveId, scopedDashboard, scopedProfile, isScopedLoading, selectStave } = useSelectedStave()
const { runAllChecks: apiRunAllChecks } = useClefs()

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

// Intelligence Pulse — derived from dashboard metrics intelligence section
const intelligence = computed(() => {
  const data = dashboardMetrics.value?.intelligence
  if (!data) return null

  const score = data.avg_health_score ?? 0
  const maxArc = 198 // 75% of circumference (r=42, C≈264)
  const arcLength = maxArc * Math.min(Math.max(score, 0), 100) / 100
  const arcColor = score >= 80 ? '#2ed573' : score >= 50 ? '#ffa502' : '#ff4757'
  const activeSources = dashboardMetrics.value?.active_sources ?? 0
  const profiledRatio =
    activeSources > 0 ? Math.min(100, Math.round((data.profiled_sources / activeSources) * 100)) : 0

  return {
    avgHealthScore: score,
    arcLength,
    arcColor,
    totalReports: data.total_reports ?? 0,
    profiledSources: data.profiled_sources ?? 0,
    pendingSuggestions: data.pending_suggestions ?? 0,
    insightAnomalies: data.insight_anomalies ?? 0,
    criticalAnomalies: data.critical_anomalies ?? 0,
    profiledRatio,
    topSuggestions: data.top_suggestions ?? [],
    topAnomalies: data.top_anomalies ?? [],
    lastAnalyzedAt: data.last_analyzed_at ?? null,
    tableMetrics: data.table_metrics ?? {},
  }
})

// Top 4 table row counts for business KPI display
const topTableMetrics = computed(() => {
  if (!intelligence.value?.tableMetrics) return {}
  const entries = Object.entries(intelligence.value.tableMetrics)
    .filter(([, count]) => count > 0)
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 4)
  return Object.fromEntries(entries)
})

// Stave health scores from intelligence data
const staveHealthScores = computed<Record<string, number>>(
  () => dashboardMetrics.value?.intelligence?.stave_health_scores ?? {}
)


// Active data: scoped when a source is selected, otherwise global
const activeHealthScore = computed(() =>
  selectedStaveId.value && scopedDashboard.value
    ? scopedDashboard.value.health_score
    : intelligence.value?.avgHealthScore ?? 0
)

const activeSuggestions = computed(() =>
  selectedStaveId.value && scopedDashboard.value
    ? (scopedDashboard.value.pending_suggestions ?? []).slice(0, 3)
    : intelligence.value?.topSuggestions ?? []
)

const activeAnomalies = computed(() =>
  selectedStaveId.value && scopedDashboard.value
    ? (scopedDashboard.value.active_anomalies ?? []).slice(0, 3)
    : intelligence.value?.topAnomalies ?? []
)

// Arc gauge computeds (responsive to scoped selection)
const activeArcLength = computed(() => {
  const maxArc = 198
  return maxArc * Math.min(Math.max(activeHealthScore.value, 0), 100) / 100
})

const activeArcColor = computed(() => {
  const score = activeHealthScore.value
  return score >= 80 ? '#2ed573' : score >= 50 ? '#ffa502' : '#ff4757'
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

function formatTableName(table: string) {
  return table.replace(/_/g, ' ')
}

function formatAnalyzedAt(ts: string) {
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return 'unknown'
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatAnomalyTime(ts: string | null | undefined) {
  if (!ts) return ''
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ''
  const diffMin = Math.floor((Date.now() - date.getTime()) / 60_000)
  const relative = diffMin < 1 ? 'just now' : diffMin < 60 ? `${diffMin}m ago` : diffMin < 1440 ? `${Math.floor(diffMin / 60)}h ago` : `${Math.floor(diffMin / 1440)}d ago`
  const abs = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  return `${relative} · ${abs}`
}

function humanizeCheckType(checkType?: string) {
  if (!checkType) return 'Data quality'
  return checkType
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

// Actions
const isReanalyzing = ref(false)

async function triggerReanalyze() {
  if (isReanalyzing.value || !staves.value.length) return
  isReanalyzing.value = true
  try {
    const { insightsService } = await import('~/services/insights')
    await Promise.all(staves.value.map((s) => insightsService.triggerAnalysis(s.id).catch(() => {})))
    await new Promise((r) => setTimeout(r, 1500))
    await fetchMetrics()
  } finally {
    isReanalyzing.value = false
  }
}

async function runAllChecks() {
  isRunningChecks.value = true
  try {
    await apiRunAllChecks()
    // Wait briefly for some checks to complete
    await new Promise((resolve) => setTimeout(resolve, 1500))
    // Refresh data
    await refreshData()
  } catch (err) {
    console.error('Failed to run all checks', err)
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
  loadPrefs()
})
</script>
