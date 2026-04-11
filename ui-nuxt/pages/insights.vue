<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <p class="dm-label mb-2">AI Intelligence</p>
        <h1
          style="font-family: var(--dm-font-display); font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
        >
          Data Insights
        </h1>
        <p class="mt-2 text-sm" style="color: var(--dm-text-secondary);">
          What the AI found in your data — anomalies, findings, and actionable suggestions.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="analyzeStatus" class="text-xs text-slate-400 italic">{{ analyzeStatus }}</span>
        <UButton
          color="primary"
          icon="i-heroicons-sparkles"
          :loading="isAnalyzing"
          @click="triggerAnalysis"
        >
          Re-analyze
        </UButton>
      </div>
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

      <!-- Management View -->
      <div v-if="item.businessReport" class="intelligence-panel rounded-xl p-5 border border-blue-500/20">
        <div class="flex items-center gap-2 mb-4">
          <Icon name="i-heroicons-building-office-2" class="w-4 h-4 text-blue-400" />
          <p class="text-xs font-semibold uppercase tracking-widest text-blue-300">Management View</p>
          <span class="ml-auto text-xs font-bold px-2 py-0.5 rounded-lg"
            :class="item.businessReport.business_health_score >= 70 ? 'bg-emerald-500/15 text-emerald-400' : item.businessReport.business_health_score >= 40 ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400'">
            Business Health {{ item.businessReport.business_health_score }}/100
          </span>
        </div>

        <!-- Executive Summary -->
        <p class="text-sm text-slate-200 leading-relaxed mb-5 max-w-3xl">
          {{ item.businessReport.executive_summary }}
        </p>

        <!-- KPIs -->
        <div v-if="item.businessReport.kpis.length" class="flex flex-wrap gap-3 mb-5">
          <div
            v-for="kpi in item.businessReport.kpis"
            :key="kpi.name"
            class="px-3 py-2 rounded-lg bg-slate-700/40 border border-slate-600/30"
          >
            <p class="text-[10px] uppercase tracking-widest text-slate-500 mb-0.5">{{ kpi.label }}</p>
            <div class="flex items-baseline gap-1">
              <span class="text-lg font-bold text-white font-mono">
                {{ kpi.unit === '$' ? '$' : '' }}{{ typeof kpi.value === 'number' ? kpi.value.toLocaleString('en', {maximumFractionDigits: 1}) : kpi.value }}{{ kpi.unit !== '$' ? ' ' + kpi.unit : '' }}
              </span>
              <Icon
                :name="kpi.trend_direction === 'up' ? 'i-heroicons-arrow-trending-up' : kpi.trend_direction === 'down' ? 'i-heroicons-arrow-trending-down' : 'i-heroicons-minus'"
                class="w-3.5 h-3.5"
                :class="kpi.trend_direction === 'up' ? 'text-emerald-400' : kpi.trend_direction === 'down' ? 'text-red-400' : 'text-slate-500'"
              />
            </div>
            <p v-if="kpi.vs_benchmark" class="text-[10px] text-slate-500 mt-0.5">{{ kpi.vs_benchmark }}</p>
          </div>
        </div>

        <!-- Performers -->
        <div v-if="item.businessReport.top_performers.length || item.businessReport.bottom_performers.length"
          class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">

          <!-- Top -->
          <div v-if="item.businessReport.top_performers.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-2">Top Performers</p>
            <div class="space-y-2">
              <div
                v-for="p in item.businessReport.top_performers"
                :key="p.entity_name"
                class="p-3 rounded-lg bg-emerald-500/8 border border-emerald-500/15"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-emerald-300 capitalize">{{ p.entity_type }}: {{ p.entity_name }}</span>
                  <span class="text-xs font-mono text-emerald-400">+{{ p.vs_average.toFixed(1) }}% avg</span>
                </div>
                <p class="text-xs text-slate-400 leading-relaxed">{{ p.drill_down_explanation }}</p>
              </div>
            </div>
          </div>

          <!-- Bottom -->
          <div v-if="item.businessReport.bottom_performers.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-red-400 mb-2">Needs Attention</p>
            <div class="space-y-2">
              <div
                v-for="p in item.businessReport.bottom_performers"
                :key="p.entity_name"
                class="p-3 rounded-lg bg-red-500/8 border border-red-500/15"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-red-300 capitalize">{{ p.entity_type }}: {{ p.entity_name }}</span>
                  <span class="text-xs font-mono text-red-400">{{ p.vs_average.toFixed(1) }}% avg</span>
                </div>
                <p class="text-xs text-slate-400 leading-relaxed">{{ p.drill_down_explanation }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Trends -->
        <div v-if="item.businessReport.trends.length" class="flex flex-wrap gap-2 mb-4">
          <span
            v-for="trend in item.businessReport.trends"
            :key="trend.metric"
            class="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border"
            :class="trend.direction === 'up' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : trend.direction === 'down' ? 'bg-red-500/10 border-red-500/20 text-red-300' : 'bg-slate-700/30 border-slate-600/20 text-slate-400'"
          >
            <Icon
              :name="trend.direction === 'up' ? 'i-heroicons-arrow-trending-up' : trend.direction === 'down' ? 'i-heroicons-arrow-trending-down' : 'i-heroicons-minus'"
              class="w-3 h-3"
            />
            {{ trend.metric }}: {{ trend.direction === 'up' ? '+' : trend.direction === 'down' ? '-' : '' }}{{ trend.magnitude.toFixed(1) }}% · {{ trend.timeframe }}
          </span>
        </div>

        <!-- Opportunities + Risks -->
        <div v-if="item.businessReport.opportunities.length || item.businessReport.risks.length"
          class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-if="item.businessReport.opportunities.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-amber-400 mb-2">Opportunities</p>
            <ul class="space-y-1">
              <li v-for="(opp, i) in item.businessReport.opportunities" :key="i"
                class="flex items-start gap-1.5 text-xs text-slate-300">
                <Icon name="i-heroicons-arrow-right" class="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                {{ opp }}
              </li>
            </ul>
          </div>
          <div v-if="item.businessReport.risks.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-red-400 mb-2">Risks</p>
            <ul class="space-y-1">
              <li v-for="(risk, i) in item.businessReport.risks" :key="i"
                class="flex items-start gap-1.5 text-xs text-slate-300">
                <Icon name="i-heroicons-exclamation-circle" class="w-3 h-3 text-red-400 mt-0.5 flex-shrink-0" />
                {{ risk }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Management View skeleton (no BI report yet) -->
      <div v-else class="intelligence-panel rounded-xl p-4 border border-slate-700/30">
        <div class="flex items-center gap-2">
          <Icon name="i-heroicons-building-office-2" class="w-4 h-4 text-slate-600" />
          <p class="text-xs text-slate-600">Business analysis not yet available — run a full analysis to generate the management view.</p>
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
                  stroke-dashoffset="0"
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
              <!-- Timestamps -->
              <div class="flex flex-wrap gap-x-4 gap-y-0.5 mt-2 pt-2 border-t border-red-500/10">
                <span class="flex items-center gap-1 text-[11px] text-slate-500">
                  <Icon name="i-heroicons-magnifying-glass" class="w-3 h-3" />
                  Detected {{ formatTimeAgo(ano.detected_at ?? item.dashboard?.last_analyzed_at) }}
                  <span class="text-slate-600">·</span>
                  <span class="text-slate-600">{{ formatDate(ano.detected_at ?? item.dashboard?.last_analyzed_at) }}</span>
                </span>
                <span v-if="ano.snapshot_at" class="flex items-center gap-1 text-[11px] text-slate-500">
                  <Icon name="i-heroicons-camera" class="w-3 h-3" />
                  Last snapshot {{ formatTimeAgo(ano.snapshot_at) }}
                  <span class="text-slate-600">·</span>
                  <span class="text-slate-600">{{ formatDate(ano.snapshot_at) }}</span>
                </span>
              </div>
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
        <div class="space-y-4">
          <div
            v-for="sug in item.dashboard.pending_suggestions"
            :key="sug.id"
            class="flex gap-3 p-4 rounded-lg bg-amber-500/8 border border-amber-500/20"
            @mouseenter="markRead(item.staveId, sug)"
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
              <div class="flex items-center gap-2 flex-wrap mb-1">
                <span class="text-xs font-medium text-amber-300 capitalize">{{ sug.category }}</span>
                <span v-if="sug.assigned_to" class="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-300">
                  <Icon name="i-heroicons-user" class="w-3 h-3" />
                  {{ sug.assigned_to }}
                </span>
              </div>
              <p class="text-sm text-slate-200 font-medium leading-snug">{{ sug.action }}</p>
              <p v-if="sug.reasoning" class="text-xs text-slate-400 mt-1.5 leading-relaxed">{{ sug.reasoning }}</p>
              <p v-if="sug.based_on" class="text-xs text-slate-500 mt-1">Based on: {{ sug.based_on }}</p>

              <!-- Lifecycle timeline -->
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 pt-3 border-t border-amber-500/10">
                <!-- Suggested -->
                <span class="flex items-center gap-1 text-[11px] text-slate-500">
                  <Icon name="i-heroicons-clock" class="w-3 h-3" />
                  Suggested {{ formatTimeAgo(sug.created_at) }}
                  <span class="text-slate-600">·</span>
                  <span class="text-slate-600">{{ formatDate(sug.created_at) }}</span>
                </span>
                <!-- Read -->
                <span v-if="sug.read_at" class="flex items-center gap-1 text-[11px] text-slate-500">
                  <Icon name="i-heroicons-eye" class="w-3 h-3 text-blue-400" />
                  <span class="text-blue-300">Read</span> by <span class="text-blue-300">{{ sug.read_by }}</span>
                  <span class="text-slate-600">·</span>
                  <span class="text-slate-600">{{ formatDate(sug.read_at) }}</span>
                </span>
                <span v-else class="flex items-center gap-1 text-[11px] text-slate-600">
                  <Icon name="i-heroicons-eye-slash" class="w-3 h-3" />
                  Unread
                </span>
                <!-- Assigned -->
                <span v-if="sug.assigned_at" class="flex items-center gap-1 text-[11px] text-slate-500">
                  <Icon name="i-heroicons-user-circle" class="w-3 h-3 text-indigo-400" />
                  <span class="text-indigo-300">Assigned to {{ sug.assigned_to }}</span>
                  <span class="text-slate-600">·</span>
                  <span class="text-slate-600">{{ formatDate(sug.assigned_at) }}</span>
                </span>
              </div>
            </div>

            <!-- Action buttons -->
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
                color="red"
                variant="ghost"
                icon="i-heroicons-x-mark"
                @click="openDismissModal(item.staveId, sug)"
              >
                Dismiss
              </UButton>
              <UButton
                v-if="!sug.assigned_to"
                size="xs"
                color="indigo"
                variant="ghost"
                icon="i-heroicons-user-plus"
                :loading="assigningId === sug.id"
                @click="assignToMe(item.staveId, sug)"
              >
                Assign me
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Suggestion History -->
      <div
        v-if="item.allSuggestions.filter(s => s.status !== 'pending').length > 0"
        class="intelligence-panel rounded-xl p-5"
      >
        <div class="flex items-center gap-2 mb-4">
          <Icon name="i-heroicons-archive-box" class="w-4 h-4 text-slate-400" />
          <p class="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Suggestion History
          </p>
          <span class="text-xs text-slate-600">({{ item.allSuggestions.filter(s => s.status !== 'pending').length }} resolved)</span>
        </div>
        <div class="space-y-3">
          <div
            v-for="sug in item.allSuggestions.filter(s => s.status !== 'pending')"
            :key="sug.id"
            class="flex gap-3 p-3 rounded-lg"
            :class="sug.status === 'accepted' ? 'bg-emerald-500/8 border border-emerald-500/15' : 'bg-slate-700/20 border border-slate-600/20'"
          >
            <!-- Status icon -->
            <div class="flex-shrink-0 mt-0.5">
              <span
                class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
                :class="sug.status === 'accepted' ? 'bg-emerald-500/25 text-emerald-300' : 'bg-slate-600/40 text-slate-400'"
              >
                <Icon :name="sug.status === 'accepted' ? 'i-heroicons-check' : 'i-heroicons-x-mark'" class="w-3 h-3 inline" />
                {{ sug.status }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-0.5">
                <span
                  class="text-[10px] font-bold uppercase px-1 py-0.5 rounded"
                  :class="sug.priority === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/15 text-amber-500'"
                >{{ sug.priority }}</span>
                <span class="text-xs text-slate-500 capitalize">{{ sug.category }}</span>
              </div>
              <p class="text-sm text-slate-300 leading-snug">{{ sug.action }}</p>
              <!-- Dismiss reason -->
              <p v-if="sug.dismiss_reason" class="text-xs text-slate-500 mt-1 italic">
                <Icon name="i-heroicons-chat-bubble-left" class="w-3 h-3 inline mr-0.5" />Reason: {{ sug.dismiss_reason }}
              </p>
              <!-- Timeline -->
              <div class="flex flex-wrap gap-x-4 gap-y-0.5 mt-2">
                <span class="flex items-center gap-1 text-[11px] text-slate-600">
                  <Icon name="i-heroicons-clock" class="w-3 h-3" />
                  Suggested {{ formatDate(sug.created_at) }}
                </span>
                <span v-if="sug.read_at" class="flex items-center gap-1 text-[11px] text-slate-600">
                  <Icon name="i-heroicons-eye" class="w-3 h-3" />
                  Read by {{ sug.read_by }} · {{ formatDate(sug.read_at) }}
                </span>
                <span v-if="sug.assigned_to" class="flex items-center gap-1 text-[11px] text-slate-600">
                  <Icon name="i-heroicons-user" class="w-3 h-3" />
                  Assigned to {{ sug.assigned_to }} · {{ formatDate(sug.assigned_at) }}
                </span>
                <span class="flex items-center gap-1 text-[11px]" :class="sug.status === 'accepted' ? 'text-emerald-600' : 'text-slate-600'">
                  <Icon :name="sug.status === 'accepted' ? 'i-heroicons-check-circle' : 'i-heroicons-x-circle'" class="w-3 h-3" />
                  {{ sug.status === 'accepted' ? 'Accepted' : 'Dismissed' }} {{ formatDate(sug.resolved_at) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- Dismiss modal -->
  <div v-if="dismissModal.open" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="dismissModal.open = false">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" />
    <div class="relative intelligence-panel rounded-2xl p-6 w-full max-w-md shadow-2xl">
      <div class="flex items-start gap-3 mb-4">
        <div class="w-9 h-9 rounded-xl bg-red-500/20 flex items-center justify-center flex-shrink-0">
          <Icon name="i-heroicons-x-mark" class="w-5 h-5 text-red-400" />
        </div>
        <div>
          <h3 class="font-semibold text-white">Dismiss suggestion</h3>
          <p class="text-xs text-slate-400 mt-0.5 leading-relaxed line-clamp-2">{{ dismissModal.suggestion?.action }}</p>
        </div>
      </div>
      <div class="mb-5">
        <label class="text-xs font-medium text-slate-400 mb-1.5 block">Reason <span class="text-slate-600">(optional)</span></label>
        <textarea
          v-model="dismissModal.reason"
          rows="3"
          placeholder="e.g. Already addressed by recent pipeline change…"
          class="w-full rounded-lg bg-slate-800/60 border border-slate-700 text-sm text-slate-200 placeholder-slate-600 px-3 py-2 resize-none focus:outline-none focus:border-blue-500/60"
        />
      </div>
      <div class="flex gap-3">
        <UButton
          color="red"
          :loading="isDismissing"
          class="flex-1"
          @click="confirmDismiss"
        >
          Dismiss
        </UButton>
        <UButton
          color="gray"
          variant="ghost"
          class="flex-1"
          @click="dismissModal.open = false"
        >
          Cancel
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { insightsService, type InsightDashboard, type InsightReport, type DataProfile, type InsightSuggestion, type BusinessReport } from '~/services/insights'
import { useAuthStore } from '~/stores/auth'

definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({ title: 'Insights - DataMetronome' })

const { staves, fetchStaves } = useStaves()
const authStore = useAuthStore()
const currentUser = computed(() => authStore.user?.username ?? 'admin')

interface StaveInsight {
  staveId: string
  staveName: string
  dashboard: InsightDashboard | null
  report: InsightReport | null
  profile: DataProfile | null
  allSuggestions: InsightSuggestion[]
  businessReport: BusinessReport | null
}

const isLoading = ref(true)
const isAnalyzing = ref(false)
const analyzeStatus = ref('')
const acceptingId = ref<string | null>(null)
const assigningId = ref<string | null>(null)
const staveInsights = ref<StaveInsight[]>([])

// Dismiss modal state
const dismissModal = ref<{ open: boolean; staveId: string; suggestion: InsightSuggestion | null; reason: string }>({
  open: false, staveId: '', suggestion: null, reason: '',
})
const isDismissing = ref(false)

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
          allSuggestions: [],
          businessReport: null,
        }
        try {
          const [dashboard, report, profile, allSuggestions] = await Promise.all([
            insightsService.getDashboard(stave.id),
            insightsService.getLatestReport(stave.id),
            insightsService.getProfile(stave.id),
            insightsService.getAllSuggestions(stave.id),
          ])
          item.dashboard = dashboard
          item.report = report
          item.profile = profile
          item.allSuggestions = allSuggestions
          item.businessReport = dashboard?.business_report ?? null
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

/** Trigger analysis and poll until the task completes (up to 3 minutes). */
async function triggerAnalysis() {
  isAnalyzing.value = true
  analyzeStatus.value = 'Dispatching…'
  try {
    // Trigger for all staves and collect task IDs
    const tasks = await Promise.all(
      staves.value.map(async (s) => {
        try {
          const t = await insightsService.triggerAnalysis(s.id)
          return { staveId: s.id, taskId: t.task_id }
        } catch {
          return null
        }
      }),
    )
    const validTasks = tasks.filter(Boolean) as { staveId: string; taskId: string }[]

    if (validTasks.length === 0) {
      analyzeStatus.value = 'Failed to dispatch'
      return
    }

    analyzeStatus.value = 'Analyzing… (this takes ~30s)'

    // Poll until all tasks complete or 3-minute timeout
    const deadline = Date.now() + 3 * 60_000
    let pending = [...validTasks]
    while (pending.length > 0 && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 4000))
      const checks = await Promise.all(
        pending.map(async (t) => {
          try {
            const status = await insightsService.pollAnalysis(t.staveId, t.taskId)
            return { ...t, done: status.status === 'completed' || status.status === 'unknown' }
          } catch {
            return { ...t, done: true }
          }
        }),
      )
      pending = checks.filter((c) => !c.done)
      if (pending.length > 0) {
        analyzeStatus.value = `Analyzing… (${pending.length} remaining)`
      }
    }

    analyzeStatus.value = 'Done! Refreshing…'
    await loadInsights()
    analyzeStatus.value = ''
  } finally {
    isAnalyzing.value = false
  }
}

async function acceptSuggestion(staveId: string, sug: InsightSuggestion) {
  acceptingId.value = sug.id
  try {
    const result = await insightsService.acceptSuggestion(staveId, sug.id)
    if (result?.check_created) {
      analyzeStatus.value = 'Suggestion accepted — monitoring check created'
      setTimeout(() => { analyzeStatus.value = '' }, 4000)
    }
    await loadInsights()
  } finally {
    acceptingId.value = null
  }
}

function openDismissModal(staveId: string, sug: InsightSuggestion) {
  dismissModal.value = { open: true, staveId, suggestion: sug, reason: '' }
}

async function confirmDismiss() {
  if (!dismissModal.value.suggestion) return
  isDismissing.value = true
  try {
    await insightsService.dismissSuggestion(
      dismissModal.value.staveId,
      dismissModal.value.suggestion.id,
      dismissModal.value.reason || undefined,
    )
    dismissModal.value.open = false
    await loadInsights()
  } finally {
    isDismissing.value = false
  }
}

async function assignToMe(staveId: string, sug: InsightSuggestion) {
  assigningId.value = sug.id
  try {
    await insightsService.assign(staveId, sug.id, currentUser.value)
    await loadInsights()
  } finally {
    assigningId.value = null
  }
}

async function markRead(staveId: string, sug: InsightSuggestion) {
  if (sug.read_at) return
  try {
    await insightsService.markRead(staveId, sug.id, currentUser.value)
    // Update local state immediately without full reload
    const item = staveInsights.value.find((i) => i.staveId === staveId)
    if (item?.dashboard) {
      const s = item.dashboard.pending_suggestions.find((s) => s.id === sug.id)
      if (s) {
        s.read_at = new Date().toISOString()
        s.read_by = currentUser.value
      }
    }
  } catch { /* silent */ }
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

function formatDate(ts?: string | null) {
  if (!ts) return null
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(loadInsights)
</script>
