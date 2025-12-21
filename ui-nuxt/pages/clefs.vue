<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">🎵 Clefs</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Configure and manage your data quality checks and monitoring rules.
        </p>
      </div>
      <div class="flex gap-3">
        <UButton
          color="gray"
          variant="outline"
          icon="i-heroicons-funnel"
          @click="showFilters = !showFilters"
        >
          Filters
        </UButton>
        <UButton
          color="purple"
          variant="outline"
          icon="i-heroicons-wand-magic-sparkles"
          @click="showVisualBuilder = true"
        >
          Visual Builder
        </UButton>
        <UButton color="primary" icon="i-heroicons-plus" @click="showCreateModal = true">
          Create Clef
        </UButton>
      </div>
    </div>

    <!-- Filters -->
    <UCard v-if="showFilters" class="border-l-4 border-l-blue-500">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UFormGroup label="Check Type">
          <USelect
            v-model="filters.checkType"
            :options="checkTypeOptions"
            placeholder="All types"
            @change="applyFilters"
          />
        </UFormGroup>
        <UFormGroup label="Stave">
          <USelect
            v-model="filters.staveId"
            :options="staveOptions"
            placeholder="All staves"
            @change="applyFilters"
          />
        </UFormGroup>
        <UFormGroup label="Status">
          <USelect
            v-model="filters.status"
            :options="statusOptions"
            placeholder="All statuses"
            @change="applyFilters"
          />
        </UFormGroup>
        <UFormGroup label="Tier">
          <USelect
            v-model="filters.tier"
            :options="tierOptions"
            placeholder="All tiers"
            @change="applyFilters"
          />
        </UFormGroup>
      </div>
    </UCard>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Clefs</p>
            <p class="text-2xl font-bold text-gray-900 dark:text-white">
              {{ filteredClefs.length }}
            </p>
          </div>
          <Icon name="i-heroicons-musical-note" class="w-8 h-8 text-blue-500" />
        </div>
      </UCard>

      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Active</p>
            <p class="text-2xl font-bold text-green-600">{{ activeClefsCount }}</p>
          </div>
          <Icon name="i-heroicons-check-circle" class="w-8 h-8 text-green-500" />
        </div>
      </UCard>

      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Failed</p>
            <p class="text-2xl font-bold text-red-600">{{ failedChecksCount }}</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 text-red-500" />
        </div>
      </UCard>

      <UCard class="hover:shadow-lg transition-shadow">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">Templates</p>
            <p class="text-2xl font-bold text-purple-600">{{ clefTemplates.length }}</p>
          </div>
          <Icon name="i-heroicons-document-duplicate" class="w-8 h-8 text-purple-500" />
        </div>
      </UCard>
    </div>

    <!-- Clefs Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      <UCard
        v-for="clef in filteredClefs"
        :key="clef.id"
        class="hover:shadow-lg transition-all duration-200 hover:scale-105 cursor-pointer"
        :class="getClefCardClass(clef)"
        @click="openClefDetails(clef)"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Icon :name="getClefIcon(clef.check_type)" class="w-5 h-5" />
              <h3 class="font-semibold text-gray-900 dark:text-white truncate">
                {{ clef.name }}
              </h3>
            </div>
            <div class="flex items-center gap-1">
              <UBadge :color="getTierColor(getClefTier(clef.check_type))" variant="soft" size="xs">
                T{{ getClefTier(clef.check_type) }}
              </UBadge>
              <UDropdown :items="getClefActions(clef)">
                <UButton
                  color="gray"
                  variant="ghost"
                  icon="i-heroicons-ellipsis-vertical"
                  size="xs"
                />
              </UDropdown>
            </div>
          </div>
        </template>

        <div class="space-y-3">
          <p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
            {{ clef.description || 'No description provided' }}
          </p>

          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500">Type:</span>
            <UBadge :color="getCheckTypeColor(clef.check_type)" variant="soft">
              {{ formatCheckType(clef.check_type) }}
            </UBadge>
          </div>

          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500">Stave:</span>
            <span class="font-medium">{{ getStaveName(clef.stave_id) }}</span>
          </div>

          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500">Schedule:</span>
            <span class="font-medium">{{ clef.schedule || 'Manual' }}</span>
          </div>

          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500">Last Result:</span>
            <div v-if="latestStatusByClef[clef.id]" class="flex items-center gap-2">
              <UBadge
                :color="getStatusBadgeColor(latestStatusByClef[clef.id]?.status)"
                variant="soft"
              >
                {{ formatStatusLabel(latestStatusByClef[clef.id]?.status) }}
              </UBadge>
              <span class="text-xs text-gray-500">
                {{ formatRelativeTime(latestStatusByClef[clef.id]?.timestamp) }}
              </span>
            </div>
            <span v-else class="text-gray-400">No runs yet</span>
          </div>

          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500">Status:</span>
            <UBadge :color="clef.is_active ? 'green' : 'gray'" variant="soft">
              {{ clef.is_active ? 'Active' : 'Inactive' }}
            </UBadge>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center justify-between" @click.stop>
            <div class="text-xs text-gray-500">Created {{ formatDate(clef.created_at) }}</div>
            <div class="flex gap-2">
              <UButton
                size="xs"
                color="blue"
                variant="ghost"
                icon="i-heroicons-play"
                @click.stop="runCheck(clef.id)"
                :loading="runningChecks.has(clef.id)"
              >
                Run
              </UButton>
              <UButton
                size="xs"
                color="purple"
                variant="ghost"
                icon="i-heroicons-clock"
                @click.stop="viewCheckHistory(clef)"
              >
                History
              </UButton>
              <UButton
                size="xs"
                color="gray"
                variant="ghost"
                icon="i-heroicons-pencil"
                @click.stop="editClef(clef)"
              >
                Edit
              </UButton>
            </div>
          </div>
        </template>
      </UCard>
    </div>

    <!-- Empty State -->
    <UCard v-if="filteredClefs.length === 0" class="text-center py-12">
      <Icon name="i-heroicons-musical-note" class="w-16 h-16 mx-auto text-gray-400 mb-4" />
      <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Clefs Found</h3>
      <p class="text-gray-600 dark:text-gray-400 mb-6">
        {{
          clefs.length === 0
            ? 'Create your first clef to start monitoring data quality.'
            : 'Try adjusting your filters to see more results.'
        }}
      </p>
      <UButton
        v-if="clefs.length === 0"
        color="primary"
        icon="i-heroicons-plus"
        @click="showCreateModal = true"
      >
        Create Your First Clef
      </UButton>
    </UCard>

    <!-- Create/Edit Modal -->
    <UModal v-model="showCreateModal" :ui="{ width: 'w-full sm:max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingClef ? 'Edit Clef' : 'Create New Clef' }}
            </h3>
            <UButton color="gray" variant="ghost" icon="i-heroicons-x-mark" @click="closeModal" />
          </div>
        </template>

        <div class="space-y-6">
          <!-- Clef Type Selection -->
          <div v-if="!editingClef">
            <h4 class="text-md font-medium mb-4">Choose Clef Type</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <UCard
                v-for="template in clefTemplates"
                :key="template.type"
                class="cursor-pointer hover:shadow-lg transition-all hover:scale-105"
                :class="{ 'ring-2 ring-blue-500': newClef.check_type === template.type }"
                @click="selectClefType(template.type)"
              >
                <div class="text-center space-y-2">
                  <Icon :name="template.icon" class="w-8 h-8 mx-auto text-blue-500" />
                  <h5 class="font-medium">{{ template.name }}</h5>
                  <p class="text-xs text-gray-600 dark:text-gray-400">{{ template.description }}</p>
                  <UBadge :color="getTierColor(template.tier)" variant="soft" size="xs">
                    Tier {{ template.tier }}
                  </UBadge>
                </div>
              </UCard>
            </div>
          </div>

          <!-- Clef Configuration Form -->
          <div v-if="newClef.check_type">
            <UForm :state="newClef" @submit="saveClef" class="space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Name" required>
                  <UInput v-model="newClef.name" placeholder="Enter clef name" />
                </UFormGroup>

                <UFormGroup label="Stave" required>
                  <USelect
                    v-model="newClef.stave_id"
                    :options="staveOptions"
                    placeholder="Select stave"
                  />
                </UFormGroup>
              </div>

              <UFormGroup label="Description">
                <UTextarea
                  v-model="newClef.description"
                  placeholder="Describe what this clef checks"
                  rows="2"
                />
              </UFormGroup>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Schedule">
                  <USelect
                    v-model="newClef.schedule"
                    :options="scheduleOptions"
                    placeholder="Select schedule"
                  />
                </UFormGroup>

                <UFormGroup label="Status">
                  <UToggle v-model="newClef.is_active" />
                  <span class="ml-2 text-sm text-gray-600 dark:text-gray-400">
                    {{ newClef.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </UFormGroup>
              </div>

              <!-- Dynamic Configuration Based on Clef Type -->
              <div class="border-t pt-4">
                <h4 class="text-md font-medium mb-4">Configuration</h4>
                <ClefConfigForm
                  :clef-type="newClef.check_type"
                  :config="newClef.configuration"
                  @update:config="newClef.configuration = $event"
                />
              </div>

              <!-- Severity Configuration -->
              <div class="border-t pt-4">
                <h4 class="text-md font-medium mb-4">Severity Thresholds</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Warning Threshold">
                    <UInput v-model="newClef.warn" placeholder="e.g., > 5%" />
                  </UFormGroup>
                  <UFormGroup label="Failure Threshold">
                    <UInput v-model="newClef.fail" placeholder="e.g., > 20%" />
                  </UFormGroup>
                </div>
              </div>

              <div class="flex justify-end gap-3 pt-4 border-t">
                <UButton color="gray" variant="outline" @click="closeModal"> Cancel </UButton>
                <UButton type="submit" color="primary" :loading="isSaving">
                  {{ editingClef ? 'Update' : 'Create' }} Clef
                </UButton>
              </div>
            </UForm>
          </div>
        </div>
      </UCard>
    </UModal>

    <!-- Visual Builder Modal -->
    <UModal v-model="showVisualBuilder" :ui="{ width: 'w-full sm:max-w-6xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Visual Clef Builder</h3>
            <UButton color="gray" variant="ghost" icon="i-heroicons-x-mark" @click="closeModal" />
          </div>
        </template>

        <ClefVisualBuilder
          :clef-templates="clefTemplates"
          :stave-options="staveOptions"
          :schedule-options="scheduleOptions"
          @create="handleVisualBuilderCreate"
          @cancel="closeModal"
        />
      </UCard>
    </UModal>

    <!-- Clef Details Modal -->
    <UModal v-model="showDetailsModal" :ui="{ width: 'w-full sm:max-w-5xl' }">
      <UCard v-if="selectedClef">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <Icon :name="getClefIcon(selectedClef.check_type)" class="w-6 h-6" />
              <div>
                <h3 class="text-lg font-semibold">{{ selectedClef.name }}</h3>
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  {{ formatCheckType(selectedClef.check_type) }} • Tier
                  {{ getClefTier(selectedClef.check_type) }}
                </p>
              </div>
            </div>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="closeDetailsModal"
            />
          </div>
        </template>

        <div class="space-y-6">
          <!-- Check Details -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
              <div>
                <h4 class="font-semibold mb-2">Description</h4>
                <p class="text-gray-700 dark:text-gray-200">
                  {{ selectedClef.description || 'No description provided' }}
                </p>
              </div>

              <div>
                <h4 class="font-semibold mb-2">Configuration</h4>
                <div
                  class="rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-4"
                >
                  <pre class="text-xs overflow-auto whitespace-pre-wrap">{{
                    formatJson(selectedClef.configuration || {})
                  }}</pre>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <h4 class="font-semibold mb-2">Stave</h4>
                  <p class="text-gray-700 dark:text-gray-200">
                    {{ getStaveName(selectedClef.stave_id) }}
                  </p>
                </div>
                <div>
                  <h4 class="font-semibold mb-2">Schedule</h4>
                  <p class="text-gray-700 dark:text-gray-200">
                    {{ selectedClef.schedule || 'Manual' }}
                  </p>
                </div>
                <div>
                  <h4 class="font-semibold mb-2">Status</h4>
                  <UBadge :color="selectedClef.is_active ? 'green' : 'gray'" variant="soft">
                    {{ selectedClef.is_active ? 'Active' : 'Inactive' }}
                  </UBadge>
                </div>
                <div>
                  <h4 class="font-semibold mb-2">Last Run</h4>
                  <div v-if="latestStatusByClef[selectedClef.id]" class="flex items-center gap-2">
                    <UBadge
                      :color="getStatusBadgeColor(latestStatusByClef[selectedClef.id]?.status)"
                      variant="soft"
                    >
                      {{ formatStatusLabel(latestStatusByClef[selectedClef.id]?.status) }}
                    </UBadge>
                    <span class="text-xs text-gray-500">
                      {{ formatRelativeTime(latestStatusByClef[selectedClef.id]?.timestamp) }}
                    </span>
                  </div>
                  <span v-else class="text-gray-400">No runs yet</span>
                </div>
              </div>
            </div>

            <!-- Check Graph -->
            <div>
              <h4 class="font-semibold mb-2">Trends & Patterns</h4>
              <div class="h-[400px] rounded-lg border border-gray-200 dark:border-gray-800 p-4">
                <CheckTypeChart
                  :check-type="selectedClef.check_type"
                  :data="checkResultsForClef"
                  :height="400"
                  :show-legend="true"
                />
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <UButton
              color="green"
              icon="i-heroicons-play"
              :loading="runningChecks.has(selectedClef.id)"
              @click.stop="runCheck(selectedClef.id)"
            >
              Run Check Now
            </UButton>
            <UButton
              color="purple"
              variant="outline"
              icon="i-heroicons-clock"
              @click.stop="viewCheckHistory(selectedClef)"
            >
              View History
            </UButton>
            <UButton
              color="blue"
              variant="outline"
              icon="i-heroicons-pencil"
              @click.stop="editClef(selectedClef)"
            >
              Edit
            </UButton>
          </div>
        </div>
      </UCard>
    </UModal>

    <!-- Check History Modal -->
    <UModal v-model="showHistoryModal" :ui="{ width: 'w-full sm:max-w-3xl' }">
      <UCard>
        <template #header>
          <div class="flex items-start justify-between">
            <div>
              <h3 class="text-lg font-semibold">
                {{ selectedClefHistory?.name || 'Check History' }}
              </h3>
              <p class="text-sm text-gray-500">
                Latest executions for {{ selectedClefHistory?.name || 'this clef' }}
              </p>
            </div>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="closeHistoryModal"
            />
          </div>
        </template>

        <div v-if="isHistoryLoading" class="py-10 text-center text-gray-500">
          <Icon name="i-heroicons-arrow-path" class="w-6 h-6 mx-auto mb-3 animate-spin" />
          Loading history...
        </div>

        <div v-else-if="historyError" class="py-10 text-center text-red-500">
          {{ historyError }}
        </div>

        <div v-else>
          <UTable
            v-if="checkHistory.length > 0"
            :rows="checkHistory"
            :columns="historyColumns"
            class="w-full"
          >
            <template #timestamp-data="{ row }">
              {{ formatTimestamp(row.timestamp) }}
            </template>
            <template #status-data="{ row }">
              <UBadge :color="getStatusBadgeColor(row.status)" variant="soft">
                {{ formatStatusLabel(row.status) }}
              </UBadge>
            </template>
            <template #message-data="{ row }">
              {{ row.message || '—' }}
            </template>
            <template #execution_time-data="{ row }">
              {{ formatExecutionTime(row.execution_time) }}
            </template>
            <template #anomalies_count-data="{ row }">
              {{ row.anomalies_count ?? 0 }}
            </template>
          </UTable>

          <p v-else class="py-10 text-center text-gray-500">No check executions recorded yet.</p>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useClefs } from '~/composables/useClefs'
import { useStaves } from '~/composables/useStaves'
import type { Clef, CreateClefRequest } from '~/services/clefs'
import type { Check } from '~/services/checks'

// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})
useHead({
  title: 'Clefs - DataMetronome',
})

// Composables
const {
  clefs,
  checkResults,
  isLoading,
  error,
  fetchClefs,
  createClef,
  updateClef,
  deleteClef,
  runCheck: executeCheck,
  fetchLatestResults,
  fetchCheckResults,
} = useClefs()
const { staves, fetchStaves } = useStaves()

// State
const showFilters = ref(false)
const showCreateModal = ref(false)
const showVisualBuilder = ref(false)
const editingClef = ref<Clef | null>(null)
const isSaving = ref(false)
const runningChecks = ref(new Set<string>())
const showDetailsModal = ref(false)
const selectedClef = ref<Clef | null>(null)
const showHistoryModal = ref(false)
const selectedClefHistory = ref<Clef | null>(null)
const checkHistory = ref<Check[]>([])
const isHistoryLoading = ref(false)
const historyError = ref<string | null>(null)
// Local state for check results to avoid readonly issues
const localCheckResults = ref<Check[]>([])

watch(showHistoryModal, (value) => {
  if (!value) {
    selectedClefHistory.value = null
    checkHistory.value = []
    historyError.value = null
  }
})

// Filters
const filters = ref({
  checkType: '',
  staveId: '',
  status: '',
  tier: '',
})

// New clef form
const newClef = ref<CreateClefRequest>({
  name: '',
  description: '',
  stave_id: '',
  check_type: '',
  configuration: {},
  schedule: '',
  is_active: true,
  warn: '',
  fail: '',
})

// Clef templates with tier information
const clefTemplates = ref([
  {
    type: 'row_count',
    name: 'Row Count',
    description: 'Monitor the number of rows in a table',
    icon: 'i-heroicons-calculator',
    tier: 1,
    config: { table: '', expected_min: 0, expected_max: 1000000 },
  },
  {
    type: 'freshness',
    name: 'Data Freshness',
    description: 'Check how recent your data is',
    icon: 'i-heroicons-clock',
    tier: 1,
    config: { table: '', column: '', max_age_hours: 24 },
  },
  {
    type: 'column_values',
    name: 'Column Validation',
    description: 'Validate values in a specific column',
    icon: 'i-heroicons-check-circle',
    tier: 1,
    config: { table: '', column: '', validation_type: 'null_check' },
  },
  {
    type: 'forecast',
    name: 'Anomaly Detection',
    description: 'ML-powered anomaly detection',
    icon: 'i-heroicons-chart-bar',
    tier: 2,
    config: { table: '', metric: 'row_count', time_column: '', model: 'sarima' },
  },
  {
    type: 'data_profile_drift',
    name: 'Data Drift',
    description: 'Detect statistical changes in data',
    icon: 'i-heroicons-arrow-trending-up',
    tier: 2,
    config: { table: '', column: '', reference_period: 'last_30_days' },
  },
  {
    type: 'lookup_validation',
    name: 'Cross-System Check',
    description: 'Validate data across multiple systems',
    icon: 'i-heroicons-link',
    tier: 3,
    config: { source_table: '', source_column: '', lookup_source: '' },
  },
  {
    type: 'python',
    name: 'Custom Python',
    description: 'Run custom Python validation scripts',
    icon: 'i-heroicons-code-bracket',
    tier: 4,
    config: { script_path: '', function_name: '', parameters: {} },
  },
])

// Computed properties
const filteredClefs = computed(() => {
  let result = clefs.value

  if (filters.value.checkType) {
    result = result.filter((clef) => clef.check_type === filters.value.checkType)
  }
  if (filters.value.staveId) {
    result = result.filter((clef) => clef.stave_id === filters.value.staveId)
  }
  if (filters.value.status) {
    if (filters.value.status === 'active') {
      result = result.filter((clef) => clef.is_active)
    } else if (filters.value.status === 'inactive') {
      result = result.filter((clef) => !clef.is_active)
    }
  }
  if (filters.value.tier) {
    result = result.filter((clef) => getClefTier(clef.check_type) === parseInt(filters.value.tier))
  }

  return result
})

const activeClefsCount = computed(() => clefs.value.filter((clef) => clef.is_active).length)

const failedChecksCount = computed(
  () =>
    // This would come from check results in a real implementation
    0,
)

const latestStatusByClef = computed<Record<string, Check | undefined>>(() => {
  const map: Record<string, Check | undefined> = {}
  checkResults.value.forEach((result) => {
    if (!map[result.clef_id]) {
      map[result.clef_id] = result
    }
  })
  return map
})

const checkResultsForClef = computed(() => {
  if (!selectedClef.value) return []
  // Combine readonly checkResults with local results
  const allResults = [...checkResults.value, ...localCheckResults.value]
  return allResults.filter((result) => result.clef_id === selectedClef.value?.id)
})

// Options for selects
const checkTypeOptions = computed(() => [
  { label: 'All Types', value: '' },
  ...clefTemplates.value.map((template) => ({
    label: template.name,
    value: template.type,
  })),
])

const staveOptions = computed(() => [
  { label: 'All Staves', value: '' },
  ...staves.value.map((stave) => ({
    label: stave.name,
    value: stave.id,
  })),
])

const statusOptions = [
  { label: 'All Statuses', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
]

const tierOptions = [
  { label: 'All Tiers', value: '' },
  { label: 'Tier 1 (Basic)', value: '1' },
  { label: 'Tier 2 (Advanced)', value: '2' },
  { label: 'Tier 3 (Cross-System)', value: '3' },
  { label: 'Tier 4 (Custom)', value: '4' },
]

const scheduleOptions = [
  { label: 'Manual', value: '' },
  { label: 'Every Hour', value: '0 * * * *' },
  { label: 'Every 6 Hours', value: '0 */6 * * *' },
  { label: 'Daily', value: '0 0 * * *' },
  { label: 'Weekly', value: '0 0 * * 0' },
  { label: 'Monthly', value: '0 0 1 * *' },
]

const historyColumns = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'status', label: 'Status' },
  { key: 'message', label: 'Message' },
  { key: 'execution_time', label: 'Duration' },
  { key: 'anomalies_count', label: 'Anomalies' },
]

// Methods
const getClefTier = (checkType: string): number => {
  const template = clefTemplates.value.find((t) => t.type === checkType)
  return template?.tier || 1
}

const getTierColor = (tier: number): string => {
  const colors = { 1: 'blue', 2: 'green', 3: 'yellow', 4: 'purple' }
  return colors[tier as keyof typeof colors] || 'gray'
}

const getClefIcon = (checkType: string): string => {
  const template = clefTemplates.value.find((t) => t.type === checkType)
  return template?.icon || 'i-heroicons-musical-note'
}

const getCheckTypeColor = (checkType: string): string => {
  const colors: Record<string, string> = {
    row_count: 'blue',
    freshness: 'green',
    column_values: 'yellow',
    forecast: 'purple',
    data_profile_drift: 'orange',
    lookup_validation: 'red',
    python: 'gray',
  }
  return colors[checkType] || 'gray'
}

const formatCheckType = (checkType: string): string => {
  const template = clefTemplates.value.find((t) => t.type === checkType)
  return template?.name || checkType.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

const getStatusBadgeColor = (status?: string): string => {
  const normalized = status?.toLowerCase()
  if (normalized === 'pass' || normalized === 'passed') return 'green'
  if (normalized === 'warn' || normalized === 'warning') return 'yellow'
  if (normalized === 'fail' || normalized === 'failed') return 'red'
  return 'gray'
}

const formatStatusLabel = (status?: string): string => {
  if (!status) return 'Unknown'
  const normalized = status.toLowerCase()
  if (normalized === 'pass') return 'Passed'
  if (normalized === 'passed') return 'Passed'
  if (normalized === 'warn' || normalized === 'warning') return 'Warning'
  if (normalized === 'fail' || normalized === 'failed') return 'Failed'
  return status
}

const formatRelativeTime = (timestamp?: string): string => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp

  const diffMs = Date.now() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes} min ago`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours} hr${diffHours > 1 ? 's' : ''} ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  return date.toLocaleString()
}

const formatTimestamp = (timestamp?: string): string => {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleString()
}

const formatExecutionTime = (seconds?: number | null): string => {
  if (seconds === undefined || seconds === null) return '—'
  return `${seconds.toFixed(2)}s`
}

const getStaveName = (staveId: string): string => {
  const stave = staves.value.find((s) => s.id === staveId)
  return stave?.name || 'Unknown Stave'
}

const getClefCardClass = (clef: Clef): string => {
  if (!clef.is_active) return 'opacity-60'
  return ''
}

const getClefActions = (clef: Clef) => [
  [
    {
      label: 'Run Check',
      icon: 'i-heroicons-play',
      click: () => runCheck(clef.id),
    },
  ],
  [
    {
      label: 'Edit',
      icon: 'i-heroicons-pencil',
      click: () => editClef(clef),
    },
  ],
  [
    {
      label: 'Duplicate',
      icon: 'i-heroicons-document-duplicate',
      click: () => duplicateClef(clef),
    },
  ],
  [
    {
      label: clef.is_active ? 'Deactivate' : 'Activate',
      icon: clef.is_active ? 'i-heroicons-pause' : 'i-heroicons-play',
      click: () => toggleClefStatus(clef),
    },
  ],
  [
    {
      label: 'Delete',
      icon: 'i-heroicons-trash',
      click: () => deleteClefAction(clef),
    },
  ],
]

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString()
}

const formatJson = (value: any) => {
  if (!value) return '—'
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const applyFilters = () => {
  // Filters are applied automatically via computed property
}

const selectClefType = (type: string) => {
  newClef.value.check_type = type
  const template = clefTemplates.value.find((t) => t.type === type)
  if (template) {
    newClef.value.configuration = { ...template.config }
  }
}

const editClef = (clef: Clef) => {
  editingClef.value = clef
  newClef.value = {
    name: clef.name,
    description: clef.description || '',
    stave_id: clef.stave_id,
    check_type: clef.check_type,
    configuration: clef.configuration || {},
    schedule: clef.schedule || '',
    is_active: clef.is_active,
    warn: '',
    fail: '',
  }
  showCreateModal.value = true
}

const duplicateClef = (clef: Clef) => {
  editingClef.value = null
  newClef.value = {
    name: `${clef.name} (Copy)`,
    description: clef.description || '',
    stave_id: clef.stave_id,
    check_type: clef.check_type,
    configuration: clef.configuration || {},
    schedule: clef.schedule || '',
    is_active: false,
    warn: '',
    fail: '',
  }
  showCreateModal.value = true
}

const openClefDetails = async (clef: Clef) => {
  selectedClef.value = clef
  showDetailsModal.value = true

  // Fetch check history for this clef to populate the graph
  try {
    const response = await fetchCheckResults(clef.id, 50)
    // Handle both array and object response formats
    const results = Array.isArray(response) ? response : response?.results || []

    // Ensure results have check_type set from the clef
    const resultsWithType = results.map((r: any) => ({
      ...r,
      check_type: r.check_type || clef.check_type,
      clef_id: r.clef_id || clef.id,
    }))

    // Add these results to localCheckResults so the graph can display them
    // Filter out duplicates and add new ones
    const existingIds = new Set(
      [...checkResults.value, ...localCheckResults.value].map((r) => r.id),
    )
    const newResults = resultsWithType.filter((r: any) => !existingIds.has(r.id))
    localCheckResults.value = [...localCheckResults.value, ...newResults]
  } catch (error) {
    console.error('Failed to fetch check history for graph:', error)
    // Don't show error to user, just use existing data
  }
}

const closeDetailsModal = () => {
  showDetailsModal.value = false
  selectedClef.value = null
}

const viewCheckHistory = async (clef: Clef) => {
  selectedClefHistory.value = clef
  showHistoryModal.value = true
  isHistoryLoading.value = true
  historyError.value = null

  try {
    const results = await fetchCheckResults(clef.id, 10)
    checkHistory.value = results
  } catch (error) {
    historyError.value = error instanceof Error ? error.message : 'Failed to load check history'
    checkHistory.value = []
    console.error('Failed to load check history:', error)
  } finally {
    isHistoryLoading.value = false
  }
}

const closeHistoryModal = () => {
  showHistoryModal.value = false
}

const toggleClefStatus = async (clef: Clef) => {
  try {
    await updateClef(clef.id, { is_active: !clef.is_active })
    await refreshLatestResults()
  } catch (error) {
    console.error('Failed to toggle clef status:', error)
  }
}

const deleteClefAction = async (clef: Clef) => {
  if (confirm(`Are you sure you want to delete "${clef.name}"?`)) {
    try {
      await deleteClef(clef.id)
      await refreshLatestResults()
    } catch (error) {
      console.error('Failed to delete clef:', error)
    }
  }
}

const runCheck = async (clefId: string) => {
  runningChecks.value.add(clefId)
  try {
    await executeCheck(clefId)
    await refreshLatestResults()
  } catch (error) {
    console.error('Failed to run check:', error)
  } finally {
    runningChecks.value.delete(clefId)
  }
}

const saveClef = async () => {
  isSaving.value = true
  try {
    if (editingClef.value) {
      await updateClef(editingClef.value.id, newClef.value)
    } else {
      await createClef(newClef.value)
    }
    closeModal()
    await refreshLatestResults()
  } catch (error) {
    console.error('Failed to save clef:', error)
  } finally {
    isSaving.value = false
  }
}

const handleVisualBuilderCreate = async (clefData: CreateClefRequest) => {
  isSaving.value = true
  try {
    await createClef(clefData)
    closeModal()
    await refreshLatestResults()
  } catch (error) {
    console.error('Failed to create clef from visual builder:', error)
  } finally {
    isSaving.value = false
  }
}

const closeModal = () => {
  showCreateModal.value = false
  showVisualBuilder.value = false
  editingClef.value = null
  newClef.value = {
    name: '',
    description: '',
    stave_id: '',
    check_type: '',
    configuration: {},
    schedule: '',
    is_active: true,
    warn: '',
    fail: '',
  }
}

const refreshLatestResults = async () => {
  try {
    await fetchLatestResults(30)
  } catch (error) {
    console.error('Failed to refresh latest check results:', error)
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([fetchClefs(), fetchStaves(), refreshLatestResults()])
})
</script>
