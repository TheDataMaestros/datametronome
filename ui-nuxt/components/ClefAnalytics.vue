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
        <div class="mt-2">
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
        <div class="mt-2">
          <span class="text-sm text-green-600">↗ +2.3% vs last week</span>
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
        <div class="mt-2">
          <span class="text-sm text-red-600">↘ -15ms vs last week</span>
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
        <div class="mt-2">
          <span class="text-sm text-red-600">↗ +3 since yesterday</span>
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
          <TrendChart 
            :data="performanceData"
            :height="250"
            :show-legend="true"
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
import { ref, computed } from 'vue'

// Props
interface Props {
  clefs: any[]
  checkResults: any[]
}

const props = defineProps<Props>()

// State
const selectedTimeRange = ref('7d')

// Mock data - in real app, this would come from API
const analytics = ref({
  totalClefs: 24,
  newThisWeek: 3,
  successRate: 94.2,
  avgExecutionTime: 245,
  activeAlerts: 2
})

const timeRangeOptions = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' }
]

const performanceData = ref([
  { date: '2024-01-01', success: 95, failures: 2, warnings: 3 },
  { date: '2024-01-02', success: 97, failures: 1, warnings: 2 },
  { date: '2024-01-03', success: 94, failures: 3, warnings: 3 },
  { date: '2024-01-04', success: 96, failures: 2, warnings: 2 },
  { date: '2024-01-05', success: 98, failures: 1, warnings: 1 },
  { date: '2024-01-06', success: 93, failures: 4, warnings: 3 },
  { date: '2024-01-07', success: 95, failures: 2, warnings: 3 }
])

const clefTypeStats = ref([
  { name: 'Row Count', count: 8, percentage: 33, tier: 1, color: '#3B82F6' },
  { name: 'Column Values', count: 6, percentage: 25, tier: 1, color: '#10B981' },
  { name: 'Freshness', count: 4, percentage: 17, tier: 1, color: '#F59E0B' },
  { name: 'Forecast', count: 3, percentage: 12, tier: 2, color: '#8B5CF6' },
  { name: 'Data Drift', count: 2, percentage: 8, tier: 2, color: '#EF4444' },
  { name: 'Lookup Validation', count: 1, percentage: 4, tier: 3, color: '#06B6D4' }
])

const topPerformers = ref([
  { id: '1', name: 'User Email Validation', type: 'Column Values', successRate: 99.8, runs: 168 },
  { id: '2', name: 'Order Count Monitor', type: 'Row Count', successRate: 99.5, runs: 144 },
  { id: '3', name: 'Data Freshness Check', type: 'Freshness', successRate: 99.2, runs: 120 }
])

const needsAttention = ref([
  { id: '1', name: 'Payment Amount Range', issue: 'High failure rate (15%)' },
  { id: '2', name: 'User Age Validation', issue: 'Slow execution (2.3s)' },
  { id: '3', name: 'Inventory Reconciliation', issue: 'Frequent timeouts' }
])

const recentActivity = ref([
  { id: '1', type: 'success', message: 'Email validation check passed', time: '2 min ago' },
  { id: '2', type: 'warning', message: 'Order count slightly high', time: '5 min ago' },
  { id: '3', type: 'failure', message: 'Payment validation failed', time: '8 min ago' },
  { id: '4', type: 'info', message: 'New clef created: User Age Check', time: '12 min ago' }
])

const healthMetrics = ref({
  reliability: 94,
  performance: 87,
  coverage: 76,
  maintainability: 82
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













