<template>
  <div class="space-y-6">
    <!-- Analytics Header -->
    <div class="text-center">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        📊 Clef Analytics Dashboard
      </h2>
      <p class="text-gray-600 dark:text-gray-400">
        Insights and performance metrics for your data quality checks
      </p>
    </div>

    <!-- Key Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Clefs</p>
            <p class="text-3xl font-bold text-blue-600">{{ analytics.totalClefs }}</p>
          </div>
          <Icon name="i-heroicons-musical-note" class="w-8 h-8 text-blue-500" />
        </div>
        <div class="mt-2" v-if="analytics.newThisWeek > 0">
          <span class="text-sm text-green-600">+{{ analytics.newThisWeek }} this week</span>
        </div>
      </UCard>

      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Success Rate</p>
            <p class="text-3xl font-bold text-green-600">{{ analytics.successRate }}%</p>
          </div>
          <Icon name="i-heroicons-check-circle" class="w-8 h-8 text-green-500" />
        </div>
        <div class="mt-2" v-if="props.checkResults.length > 0">
          <span class="text-sm text-gray-600 dark:text-gray-400">{{ props.checkResults.length }} total checks</span>
        </div>
      </UCard>

      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Execution</p>
            <p class="text-3xl font-bold text-purple-600">{{ analytics.avgExecutionTime }}ms</p>
          </div>
          <Icon name="i-heroicons-clock" class="w-8 h-8 text-purple-500" />
        </div>
        <div class="mt-2" v-if="analytics.avgExecutionTime > 0">
          <span class="text-sm text-gray-600 dark:text-gray-400">Average execution time</span>
        </div>
      </UCard>

      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Active Alerts</p>
            <p class="text-3xl font-bold text-red-600">{{ analytics.activeAlerts }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 text-red-500" />
        </div>
        <div class="mt-2" v-if="analytics.activeAlerts > 0">
          <span class="text-sm text-red-600">Failed checks in last 24h</span>
        </div>
      </UCard>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Clef Performance Over Time -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Performance Over Time</h3>
            <USelect
              v-model="selectedTimeRange"
              :options="timeRangeOptions"
              size="sm"
            />
          </div>
        </template>

        <div class="h-64">
          <div v-if="performanceData.length === 0" class="flex items-center justify-center h-full text-gray-500">
            <div class="text-center">
              <Icon name="i-heroicons-chart-bar" class="w-12 h-12 mx-auto mb-2 text-gray-400" />
              <p>No performance data available</p>
            </div>
          </div>
          <TrendChart
            v-else
            :data="performanceData"
            :height="250"
            :show-legend="true"
            type="line"
          />
        </div>
      </UCard>

      <!-- Clef Type Distribution -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Clef Type Distribution</h3>
        </template>

        <div class="space-y-4">
          <div
            v-for="(type, index) in clefTypeStats"
            :key="type.name"
            class="flex items-center justify-between"
          >
            <div class="flex items-center space-x-3">
              <div
                class="w-4 h-4 rounded-full"
                :style="{ backgroundColor: type.color }"
              ></div>
              <div>
                <p class="font-medium">{{ type.name }}</p>
                <p class="text-sm text-gray-600 dark:text-gray-400">Tier {{ type.tier }}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="font-semibold">{{ type.count }}</p>
              <p class="text-sm text-gray-600 dark:text-gray-400">{{ type.percentage }}%</p>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Detailed Analytics -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Top Performing Clefs -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">🏆 Top Performers</h3>
        </template>

        <div class="space-y-3">
          <div v-if="topPerformers.length === 0" class="text-center py-4 text-gray-500 text-sm">
            No performance data available yet
          </div>
          <div
            v-for="(clef, index) in topPerformers"
            :key="clef.id"
            class="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg"
          >
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                {{ index + 1 }}
              </div>
              <div>
                <p class="font-medium">{{ clef.name }}</p>
                <p class="text-sm text-gray-600 dark:text-gray-400">{{ clef.type }}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="font-semibold text-green-600">{{ clef.successRate }}%</p>
              <p class="text-sm text-gray-600 dark:text-gray-400">{{ clef.runs }} runs</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Clefs Needing Attention -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">⚠️ Need Attention</h3>
        </template>

        <div class="space-y-3">
          <div v-if="needsAttention.length === 0" class="text-center py-4 text-green-600 text-sm">
            🎉 All clefs are performing well!
          </div>
          <div
            v-for="clef in needsAttention"
            :key="clef.id"
            class="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
          >
            <div class="flex items-center space-x-3">
              <Icon name="i-heroicons-exclamation-triangle" class="w-5 h-5 text-red-500" />
              <div>
                <p class="font-medium">{{ clef.name }}</p>
                <p class="text-sm text-gray-600 dark:text-gray-400">{{ clef.issue }}</p>
              </div>
            </div>
            <UButton size="xs" color="red" variant="outline">
              Fix
            </UButton>
          </div>
        </div>
      </UCard>

      <!-- Recent Activity -->
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">📈 Recent Activity</h3>
        </template>

        <div class="space-y-3">
          <div v-if="recentActivity.length === 0" class="text-center py-4 text-gray-500 text-sm">
            No recent activity
          </div>
          <div
            v-for="activity in recentActivity"
            :key="activity.id"
            class="flex items-center space-x-3 p-2"
          >
            <div
              class="w-2 h-2 rounded-full"
              :class="getActivityColor(activity.type)"
            ></div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate">{{ activity.message }}</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">{{ activity.time }}</p>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Clef Health Score -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">🎯 Overall Health Score</h3>
          <UBadge :color="getHealthScoreColor(overallHealthScore)" variant="soft">
            {{ overallHealthScore }}/100
          </UBadge>
        </div>
      </template>

      <div class="space-y-4">
        <div class="flex items-center space-x-4">
          <div class="flex-1">
            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
              <div
                class="h-3 rounded-full transition-all duration-500"
                :class="getHealthScoreColor(overallHealthScore)"
                :style="{ width: `${overallHealthScore}%` }"
              ></div>
            </div>
          </div>
          <span class="text-sm font-medium">{{ overallHealthScore }}%</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
          <div>
            <p class="text-2xl font-bold text-green-600">{{ healthMetrics.reliability }}%</p>
            <p class="text-sm text-gray-600 dark:text-gray-400">Reliability</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-blue-600">{{ healthMetrics.performance }}%</p>
            <p class="text-sm text-gray-600 dark:text-gray-400">Performance</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-purple-600">{{ healthMetrics.coverage }}%</p>
            <p class="text-sm text-gray-600 dark:text-gray-400">Coverage</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-orange-600">{{ healthMetrics.maintainability }}%</p>
            <p class="text-sm text-gray-600 dark:text-gray-400">Maintainability</p>
          </div>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Clef } from '~/services/clefs'
import type { Check } from '~/services/checks'

// Props
interface Props {
  clefs: Clef[]
  checkResults: Check[]
}

const props = defineProps<Props>()

// State
const selectedTimeRange = ref('7d')

// Computed analytics from real data
const analytics = computed(() => {
  const totalClefs = props.clefs.length
  const activeClefs = props.clefs.filter(c => c.is_active).length

  // Calculate new clefs this week
  const oneWeekAgo = new Date()
  oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
  const newThisWeek = props.clefs.filter(c => {
    const createdAt = new Date(c.created_at)
    return createdAt >= oneWeekAgo
  }).length

  // Calculate success rate from check results
  const totalChecks = props.checkResults.length
  const successfulChecks = props.checkResults.filter(c => c.status === 'success' || c.status === 'passed').length
  const successRate = totalChecks > 0 ? (successfulChecks / totalChecks) * 100 : 0

  // Calculate average execution time
  const executionTimes = props.checkResults
    .filter(c => c.execution_time !== null && c.execution_time !== undefined)
    .map(c => c.execution_time!)
  const avgExecutionTime = executionTimes.length > 0
    ? Math.round(executionTimes.reduce((a, b) => a + b, 0) / executionTimes.length)
    : 0

  // Count active alerts (failed checks in last 24 hours)
  const oneDayAgo = new Date()
  oneDayAgo.setDate(oneDayAgo.getDate() - 1)
  const activeAlerts = props.checkResults.filter(c => {
    const timestamp = new Date(c.timestamp)
    return timestamp >= oneDayAgo && (c.status === 'failed' || c.status === 'failure')
  }).length

  return {
    totalClefs,
    activeClefs,
    newThisWeek,
    successRate: Math.round(successRate * 10) / 10,
    avgExecutionTime,
    activeAlerts
  }
})

const timeRangeOptions = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' }
]

// Compute performance data from check results
const performanceData = computed(() => {
  const days = selectedTimeRange.value === '7d' ? 7 : selectedTimeRange.value === '30d' ? 30 : 90
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)

  // Group check results by date
  const resultsByDate = new Map<string, { success: number; failures: number; warnings: number }>()

  props.checkResults.forEach(check => {
    const checkDate = new Date(check.timestamp)
    if (checkDate < startDate) return

    const dateKey = checkDate.toISOString().split('T')[0]
    if (!resultsByDate.has(dateKey)) {
      resultsByDate.set(dateKey, { success: 0, failures: 0, warnings: 0 })
    }

    const dayData = resultsByDate.get(dateKey)!
    if (check.status === 'success' || check.status === 'passed') {
      dayData.success++
    } else if (check.status === 'failed' || check.status === 'failure') {
      dayData.failures++
    } else if (check.status === 'warning' || check.severity === 'warning') {
      dayData.warnings++
    }
  })

  // Fill in missing dates with zeros
  const data: Array<{ date: string; success: number; failures: number; warnings: number }> = []
  for (let i = 0; i < days; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i)
    const dateKey = date.toISOString().split('T')[0]
    const dayData = resultsByDate.get(dateKey) || { success: 0, failures: 0, warnings: 0 }
    data.push({
      date: dateKey,
      ...dayData
    })
  }

  return data
})

// Compute clef type statistics from real data
const clefTypeStats = computed(() => {
  const typeCounts = new Map<string, number>()

  props.clefs.forEach(clef => {
    const count = typeCounts.get(clef.check_type) || 0
    typeCounts.set(clef.check_type, count + 1)
  })

  const typeInfo: Record<string, { name: string; tier: number; color: string }> = {
    'row_count': { name: 'Row Count', tier: 1, color: '#3B82F6' },
    'column_values': { name: 'Column Values', tier: 1, color: '#10B981' },
    'freshness': { name: 'Freshness', tier: 1, color: '#F59E0B' },
    'forecast': { name: 'Forecast', tier: 2, color: '#8B5CF6' },
    'data_profile_drift': { name: 'Data Drift', tier: 2, color: '#EF4444' },
    'lookup_validation': { name: 'Lookup Validation', tier: 3, color: '#06B6D4' },
    'python': { name: 'Python Script', tier: 4, color: '#EC4899' }
  }

  const total = props.clefs.length
  const stats = Array.from(typeCounts.entries())
    .map(([type, count]) => {
      const info = typeInfo[type] || { name: type, tier: 1, color: '#6B7280' }
      return {
        name: info.name,
        count,
        percentage: total > 0 ? Math.round((count / total) * 100) : 0,
        tier: info.tier,
        color: info.color
      }
    })
    .sort((a, b) => b.count - a.count)

  return stats
})

// Compute top performers from real data
const topPerformers = computed(() => {
  const clefPerformance = new Map<string, { success: number; total: number; name: string; type: string }>()

  props.checkResults.forEach(check => {
    if (!check.clef_id) return

    if (!clefPerformance.has(check.clef_id)) {
      const clef = props.clefs.find(c => c.id === check.clef_id)
      clefPerformance.set(check.clef_id, {
        success: 0,
        total: 0,
        name: clef?.name || 'Unknown',
        type: clef?.check_type || 'unknown'
      })
    }

    const perf = clefPerformance.get(check.clef_id)!
    perf.total++
    if (check.status === 'success' || check.status === 'passed') {
      perf.success++
    }
  })

  return Array.from(clefPerformance.entries())
    .map(([id, perf]) => ({
      id,
      name: perf.name,
      type: formatCheckType(perf.type),
      successRate: perf.total > 0 ? Math.round((perf.success / perf.total) * 100 * 10) / 10 : 0,
      runs: perf.total
    }))
    .filter(p => p.runs > 0)
    .sort((a, b) => b.successRate - a.successRate)
    .slice(0, 3)
})

const formatCheckType = (type: string) => {
  const typeMap: Record<string, string> = {
    'row_count': 'Row Count',
    'column_values': 'Column Values',
    'freshness': 'Freshness',
    'forecast': 'Forecast',
    'data_profile_drift': 'Data Drift',
    'lookup_validation': 'Lookup Validation',
    'python': 'Python Script'
  }
  return typeMap[type] || type
}

// Compute clefs needing attention from real data
const needsAttention = computed(() => {
  const clefIssues = new Map<string, { name: string; issues: string[] }>()

  props.checkResults.forEach(check => {
    if (!check.clef_id) return

    const clef = props.clefs.find(c => c.id === check.clef_id)
    if (!clef) return

    if (!clefIssues.has(check.clef_id)) {
      clefIssues.set(check.clef_id, { name: clef.name, issues: [] })
    }

    const issue = clefIssues.get(check.clef_id)!

    // Check for high failure rate
    const recentChecks = props.checkResults
      .filter(c => c.clef_id === check.clef_id)
      .slice(-20) // Last 20 checks
    const failureRate = recentChecks.filter(c => c.status === 'failed' || c.status === 'failure').length / recentChecks.length
    if (failureRate > 0.1 && !issue.issues.some(i => i.includes('failure rate'))) {
      issue.issues.push(`High failure rate (${Math.round(failureRate * 100)}%)`)
    }

    // Check for slow execution
    if (check.execution_time && check.execution_time > 2000 && !issue.issues.some(i => i.includes('Slow execution'))) {
      issue.issues.push(`Slow execution (${Math.round(check.execution_time)}ms)`)
    }
  })

  return Array.from(clefIssues.entries())
    .filter(([_, issue]) => issue.issues.length > 0)
    .map(([id, issue]) => ({
      id,
      name: issue.name,
      issue: issue.issues[0] // Show first issue
    }))
    .slice(0, 5)
})

// Compute recent activity from real data
const recentActivity = computed(() => {
  const activities: Array<{ id: string; type: string; message: string; time: string }> = []

  // Add recent check results
  const recentChecks = [...props.checkResults]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10)

  recentChecks.forEach(check => {
    const clef = props.clefs.find(c => c.id === check.clef_id)
    const clefName = clef?.name || 'Unknown clef'

    let type = 'info'
    let message = ''

    if (check.status === 'success' || check.status === 'passed') {
      type = 'success'
      message = `${clefName} check passed`
    } else if (check.status === 'failed' || check.status === 'failure') {
      type = 'failure'
      message = `${clefName} check failed${check.message ? `: ${check.message}` : ''}`
    } else if (check.status === 'warning' || check.severity === 'warning') {
      type = 'warning'
      message = `${clefName} check warning${check.message ? `: ${check.message}` : ''}`
    } else {
      message = `${clefName} check completed`
    }

    const timestamp = new Date(check.timestamp)
    const now = new Date()
    const diffMs = now.getTime() - timestamp.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    let time = ''
    if (diffMins < 1) {
      time = 'Just now'
    } else if (diffMins < 60) {
      time = `${diffMins} min ago`
    } else if (diffHours < 24) {
      time = `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    } else {
      time = `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    }

    activities.push({
      id: check.id,
      type,
      message,
      time
    })
  })

  return activities.slice(0, 5)
})

// Compute health metrics from real data
const healthMetrics = computed(() => {
  // Reliability: based on success rate
  const totalChecks = props.checkResults.length
  const successfulChecks = props.checkResults.filter(c => c.status === 'success' || c.status === 'passed').length
  const reliability = totalChecks > 0 ? Math.round((successfulChecks / totalChecks) * 100) : 0

  // Performance: based on execution time (inverse - faster is better)
  const executionTimes = props.checkResults
    .filter(c => c.execution_time !== null && c.execution_time !== undefined)
    .map(c => c.execution_time!)
  const avgExecutionTime = executionTimes.length > 0
    ? executionTimes.reduce((a, b) => a + b, 0) / executionTimes.length
    : 0
  // Score: 100 if < 100ms, decreasing to 0 at 5000ms
  const performance = avgExecutionTime > 0
    ? Math.max(0, Math.min(100, Math.round(100 - ((avgExecutionTime - 100) / 4900) * 100)))
    : 100

  // Coverage: percentage of active clefs that have run checks
  const activeClefs = props.clefs.filter(c => c.is_active)
  const clefsWithChecks = new Set(props.checkResults.map(c => c.clef_id).filter(Boolean))
  const coverage = activeClefs.length > 0
    ? Math.round((clefsWithChecks.size / activeClefs.length) * 100)
    : 0

  // Maintainability: based on clef age and activity (newer and more active = better)
  const now = new Date()
  const clefAges = props.clefs.map(c => {
    const age = (now.getTime() - new Date(c.created_at).getTime()) / (1000 * 60 * 60 * 24) // days
    return age
  })
  const avgAge = clefAges.length > 0 ? clefAges.reduce((a, b) => a + b, 0) / clefAges.length : 0
  // Score: 100 if avg age < 30 days, decreasing to 50 at 365 days
  const maintainability = avgAge < 30 ? 100 : Math.max(50, Math.round(100 - ((avgAge - 30) / 335) * 50))

  return {
    reliability,
    performance,
    coverage,
    maintainability
  }
})

// Computed
const overallHealthScore = computed(() => {
  const metrics = healthMetrics.value
  return Math.round((metrics.reliability + metrics.performance + metrics.coverage + metrics.maintainability) / 4)
})

// Methods
const getActivityColor = (type: string) => {
  const colors = {
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    failure: 'bg-red-500',
    info: 'bg-blue-500'
  }
  return colors[type as keyof typeof colors] || 'bg-gray-500'
}

const getHealthScoreColor = (score: number) => {
  if (score >= 90) return 'bg-green-500'
  if (score >= 70) return 'bg-yellow-500'
  if (score >= 50) return 'bg-orange-500'
  return 'bg-red-500'
}
</script>
