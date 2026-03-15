<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <p class="dm-label mb-2">AI Intelligence</p>
        <h1
          style="font-family: var(--dm-font-display); font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
        >
          Data Insights
        </h1>
        <p class="mt-2 text-sm" style="color: var(--dm-text-secondary);">
          What the AI found in your data — anomalies, findings, and actionable suggestions.
        </p>
      </div>
      <UButton
        color="primary"
        icon="i-heroicons-sparkles"
        :loading="isAnalyzing"
        @click="triggerAnalysis"
      >
        Re-analyze
      </UButton>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="flex items-center justify-center h-64">
      <div class="text-center">
        <Icon name="i-heroicons-arrow-path" class="w-8 h-8 mx-auto text-slate-400 animate-spin mb-3" />
        <p class="text-slate-400">Loading AI insights...</p>
      </div>
    </div>

    <!-- No data state -->
    <div v-else-if="!staveInsights.length" class="intelligence-panel rounded-xl p-12 text-center">
      <Icon name="i-heroicons-sparkles" class="w-12 h-12 mx-auto text-slate-500 mb-4" />
      <h3 class="text-lg font-semibold text-white mb-2">No Insights Yet</h3>
      <p class="text-slate-400 mb-6">Run an analysis to let the AI examine your data sources.</p>
      <UButton color="primary" icon="i-heroicons-play" @click="triggerAnalysis">
        Run First Analysis
      </UButton>
    </div>

    <!-- Stave insight cards -->
    <div v-else v-for="item in staveInsights" :key="item.staveId" class="space-y-4">

      <!-- Stave header -->
      <div class="intelligence-panel rounded-xl p-5">
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-start gap-3">
            <div class="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Icon name="i-heroicons-server" class="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <h2 class="text-xl font-semibold text-white">{{ item.staveName }}</h2>
                <span v-if="item.profile" class="text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 font-semibold capitalize">
                  {{ item.profile.domain_type }}
                </span>
              </div>
              <!-- Business context — the CEO line -->
              <p v-if="item.profile?.domain_context?.business_context" class="text-sm text-slate-300 mt-1 leading-relaxed max-w-2xl">
                {{ item.profile.domain_context.business_context }}
              </p>
              <div class="flex items-center gap-3 mt-2 flex-wrap">
                <span v-if="item.profile" class="text-xs text-slate-500">
                  Domain confidence: <span class="text-slate-300 font-medium">{{ Math.round(item.profile.domain_confidence * 100) }}%</span>
                  — how certain the AI is this is an {{ item.profile.domain_type }} system
                </span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-xs text-slate-500">Analyzed {{ formatTimeAgo(item.dashboard?.last_analyzed_at) }}</span>
            <span
              class="text-xs font-semibold px-2 py-1 rounded-lg"
              :class="trendClass(item.dashboard?.health_trend)"
            >
              <Icon :name="trendIcon(item.dashboard?.health_trend)" class="w-3 h-3 inline mr-0.5" />
              {{ item.dashboard?.health_trend }}
            </span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <!-- Health + Summary -->
        <div class="intelligence-panel rounded-xl p-5 lg:col-span-1 flex flex-col gap-4">
          <!-- Score -->
          <div class="flex items-center gap-4">
            <div class="relative flex-shrink-0">
              <svg width="80" height="80" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(148,163,184,0.15)"
                  stroke-width="8" stroke-dasharray="198 264" stroke-linecap="round"
                  transform="rotate(-135 50 50)" />
                <circle cx="50" cy="50" r="42" fill="none"
                  :stroke="scoreColor(item.dashboard?.health_score ?? 0)"
                  stroke-width="8" stroke-linecap="round"
                  :stroke-dasharray="`${scoreArc(item.dashboard?.health_score ?? 0)} 264`"
                  :stroke-dashoffset="198 - scoreArc(item.dashboard?.health_score ?? 0)"
                  transform="rotate(-135 50 50)" />
                <text x="50" y="52" text-anchor="middle" fill="white" font-size="22" font-weight="700"
                  font-family="ui-monospace, monospace">{{ item.dashboard?.health_score ?? 0 }}</text>
                <text x="50" y="64" text-anchor="middle" fill="rgba(148,163,184,0.6)" font-size="8">/ 100</text>
              </svg>
            </div>
            <div>
              <p class="text-sm font-semibold" :class="scoreLabel(item.dashboard?.health_score ?? 0).color">
                {{ scoreLabel(item.dashboard?.health_score ?? 0).text }}
              </p>
              <p class="text-xs text-slate-500 mt-0.5">Health score</p>
            </div>
          </div>

          <!-- AI Summary -->
          <div v-if="item.report?.summary" class="border-t border-slate-700/50 pt-4">
            <p class="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">AI Summary</p>
            <p class="text-sm text-slate-300 leading-relaxed">{{ item.report.summary }}</p>
          </div>
        </div>

        <!-- Key Findings + Dimensions -->
        <div class="intelligence-panel rounded-xl p-5 lg:col-span-2 flex flex-col gap-4">
          <!-- Key Findings -->
          <div v-if="item.report?.key_findings?.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Key Findings</p>
            <ul class="space-y-2">
              <li
                v-for="(finding, i) in item.report.key_findings"
                :key="i"
                class="flex items-start gap-2 text-sm text-slate-300"
              >
                <Icon name="i-heroicons-arrow-right" class="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" />
                {{ finding }}
              </li>
            </ul>
          </div>

          <!-- Dimensions -->
          <div v-if="item.dashboard?.dimensions?.length" class="border-t border-slate-700/50 pt-4">
            <p class="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Quality Dimensions</p>
            <div class="space-y-2">
              <div v-for="dim in item.dashboard.dimensions" :key="dim.name" class="flex items-center gap-3">
                <span class="text-xs text-slate-400 w-28 flex-shrink-0 capitalize">{{ dim.name }}</span>
                <div class="flex-1 h-1.5 rounded-full bg-slate-700">
                  <div
                    class="h-full rounded-full transition-all"
                    :style="{ width: `${dim.score}%`, background: dimColor(dim.score) }"
                  />
                </div>
                <span class="text-xs font-medium w-8 text-right" :style="{ color: dimColor(dim.score) }">
                  {{ dim.score }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Anomalies -->
      <div v-if="item.dashboard?.active_anomalies?.length" class="intelligence-panel rounded-xl p-5">
        <div class="flex items-center gap-2 mb-4">
          <Icon name="i-heroicons-exclamation-triangle" class="w-4 h-4 text-red-400" />
          <p class="text-xs font-semibold uppercase tracking-widest text-red-300">
            {{ item.dashboard.active_anomalies.length }} Active Anomal{{ item.dashboard.active_anomalies.length !== 1 ? 'ies' : 'y' }}
          </p>
        </div>
        <div class="space-y-3">
          <div
            v-for="(ano, i) in item.dashboard.active_anomalies"
            :key="i"
            class="flex gap-3 p-4 rounded-lg bg-red-500/8 border border-red-500/20"
          >
            <div class="flex-shrink-0 mt-0.5">
              <span class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-500/30 text-red-300">
                {{ ano.severity }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs font-medium text-red-300">{{ ano.category }}</span>
                <span v-if="ano.table" class="text-xs text-slate-500">· table: <code class="text-slate-400">{{ ano.table }}</code></span>
              </div>
              <p class="text-sm text-slate-200 leading-relaxed">{{ ano.description }}</p>
              <p v-if="ano.evidence" class="text-xs text-slate-400 mt-2 leading-relaxed">
                <span class="text-slate-500">Evidence: </span>{{ ano.evidence }}
              </p>
              <p v-if="ano.compared_to" class="text-xs text-slate-500 mt-1">vs {{ ano.compared_to }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Suggestions -->
      <div v-if="item.dashboard?.pending_suggestions?.length" class="intelligence-panel rounded-xl p-5">
        <div class="flex items-center gap-2 mb-4">
          <Icon name="i-heroicons-light-bulb" class="w-4 h-4 text-amber-400" />
          <p class="text-xs font-semibold uppercase tracking-widest text-amber-300">
            {{ item.dashboard.pending_suggestions.length }} Pending Suggestion{{ item.dashboard.pending_suggestions.length !== 1 ? 's' : '' }}
          </p>
        </div>
        <div class="space-y-3">
          <div
            v-for="sug in item.dashboard.pending_suggestions"
            :key="sug.id"
            class="flex gap-3 p-4 rounded-lg bg-amber-500/8 border border-amber-500/20"
          >
            <div class="flex-shrink-0 mt-0.5">
              <span
                class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
                :class="sug.priority === 'high' ? 'bg-red-500/30 text-red-300' : 'bg-amber-500/20 text-amber-400'"
              >
                {{ sug.priority }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs font-medium text-amber-300 capitalize">{{ sug.category }}</span>
              </div>
              <p class="text-sm text-slate-200 font-medium leading-snug">{{ sug.action }}</p>
              <p v-if="sug.reasoning" class="text-xs text-slate-400 mt-1.5 leading-relaxed">{{ sug.reasoning }}</p>
              <p v-if="sug.based_on" class="text-xs text-slate-500 mt-1">Based on: {{ sug.based_on }}</p>
            </div>
            <div class="flex-shrink-0 flex flex-col gap-2">
              <UButton
                size="xs"
                color="green"
                variant="soft"
                icon="i-heroicons-check"
                :loading="acceptingId === sug.id"
                @click="acceptSuggestion(item.staveId, sug)"
              >
                Accept
              </UButton>
              <UButton
                size="xs"
                color="gray"
                variant="ghost"
                icon="i-heroicons-x-mark"
                :loading="dismissingId === sug.id"
                @click="dismissSuggestion(item.staveId, sug)"
              >
                Dismiss
              </UButton>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { insightsService, type InsightDashboard, type InsightReport, type DataProfile, type InsightSuggestion } from '~/services/insights'

definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({ title: 'Insights - DataMetronome' })

const { staves, fetchStaves } = useStaves()

interface StaveInsight {
  staveId: string
  staveName: string
  dashboard: InsightDashboard | null
  report: InsightReport | null
  profile: DataProfile | null
}

const isLoading = ref(true)
const isAnalyzing = ref(false)
const acceptingId = ref<string | null>(null)
const dismissingId = ref<string | null>(null)
const staveInsights = ref<StaveInsight[]>([])

async function loadInsights() {
  isLoading.value = true
  try {
    await fetchStaves()
    const results = await Promise.all(
      staves.value.map(async (stave) => {
        const item: StaveInsight = {
          staveId: stave.id,
          staveName: stave.name,
          dashboard: null,
          report: null,
          profile: null,
        }
        try {
          const [dashboard, report, profile] = await Promise.all([
            insightsService.getDashboard(stave.id),
            insightsService.getLatestReport(stave.id),
            insightsService.getProfile(stave.id),
          ])
          item.dashboard = dashboard
          item.report = report
          item.profile = profile
        } catch {
          // no insights for this stave yet
        }
        return item
      }),
    )
    staveInsights.value = results.filter((i) => i.dashboard !== null)
  } finally {
    isLoading.value = false
  }
}

async function triggerAnalysis() {
  isAnalyzing.value = true
  try {
    await Promise.all(staves.value.map((s) => insightsService.triggerAnalysis(s.id).catch(() => {})))
    await new Promise((r) => setTimeout(r, 2000))
    await loadInsights()
  } finally {
    isAnalyzing.value = false
  }
}

async function acceptSuggestion(staveId: string, sug: InsightSuggestion) {
  acceptingId.value = sug.id
  try {
    await insightsService.acceptSuggestion(staveId, sug.id)
    await loadInsights()
  } finally {
    acceptingId.value = null
  }
}

async function dismissSuggestion(staveId: string, sug: InsightSuggestion) {
  dismissingId.value = sug.id
  try {
    await insightsService.dismissSuggestion(staveId, sug.id)
    await loadInsights()
  } finally {
    dismissingId.value = null
  }
}

// Helpers
function scoreArc(score: number) {
  return (198 * Math.min(Math.max(score, 0), 100)) / 100
}

function scoreColor(score: number) {
  if (score >= 80) return '#2ed573'
  if (score >= 50) return '#ffa502'
  return '#ff4757'
}

function scoreLabel(score: number) {
  if (score >= 80) return { text: 'Strong', color: 'text-emerald-400' }
  if (score >= 50) return { text: 'Moderate', color: 'text-amber-400' }
  return { text: 'Needs Attention', color: 'text-red-400' }
}

function dimColor(score: number) {
  if (score >= 80) return '#2ed573'
  if (score >= 50) return '#ffa502'
  return '#ff4757'
}

function trendClass(trend?: string) {
  if (trend === 'improving') return 'bg-emerald-500/15 text-emerald-400'
  if (trend === 'declining') return 'bg-red-500/15 text-red-400'
  return 'bg-slate-700/50 text-slate-400'
}

function trendIcon(trend?: string) {
  if (trend === 'improving') return 'i-heroicons-arrow-trending-up'
  if (trend === 'declining') return 'i-heroicons-arrow-trending-down'
  return 'i-heroicons-minus'
}

function formatTimeAgo(ts?: string | null) {
  if (!ts) return 'never'
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return 'unknown'
  const diffMin = Math.floor((Date.now() - date.getTime()) / 60_000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  return `${Math.floor(diffH / 24)}d ago`
}

onMounted(loadInsights)
</script>
