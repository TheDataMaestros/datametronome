<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
          Data Sources
        </h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Manage your data source connections and configurations.
        </p>
      </div>
    </div>

    <!-- Data Sources Table -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Data Sources</h3>
          <div class="flex items-center gap-2">
            <UButton
              color="primary"
              variant="outline"
              size="sm"
              icon="i-heroicons-plus"
              @click="showAddModal = true"
            >
              Add Source
            </UButton>
                <UButton
                  color="gray"
                  variant="outline"
                  size="sm"
                  icon="i-heroicons-arrow-path"
                  @click="refreshStaves"
                  :loading="isLoading"
                >
                  Refresh
                </UButton>
          </div>
        </div>
      </template>

      <UTable
        :rows="staves"
        :columns="staveColumns"
        class="w-full"
      >
        <template #data_source_type-data="{ row }">
          <UBadge
            :color="getDataSourceTypeColor(row.data_source_type)"
            variant="subtle"
          >
            {{ row.data_source_type.toUpperCase() }}
          </UBadge>
        </template>

        <template #is_active-data="{ row }">
          <UBadge
            :color="row.is_active ? 'green' : 'gray'"
            variant="subtle"
          >
            {{ row.is_active ? 'Active' : 'Inactive' }}
          </UBadge>
        </template>

        <template #created_at-data="{ row }">
          {{ formatDate(row.created_at) }}
        </template>

        <template #actions-data="{ row }">
          <div class="flex items-center gap-2">
            <UButton
              color="blue"
              variant="ghost"
              size="sm"
              icon="i-heroicons-eye"
              @click="viewStaveDetails(row)"
            />
            <UButton
              color="green"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="testConnection(row)"
            />
            <UButton
              color="yellow"
              variant="ghost"
              size="sm"
              icon="i-heroicons-pencil"
              @click="editStave(row)"
            />
            <UButton
              color="red"
              variant="ghost"
              size="sm"
              icon="i-heroicons-trash"
              @click="deleteStave(row)"
            />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Stave Details Modal -->
    <UModal v-model="showDetailsModal" :ui="{ width: 'w-full sm:max-w-4xl' }">
      <UCard v-if="selectedStave">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Data Source Details</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showDetailsModal = false"
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
                  <span class="text-gray-600 dark:text-gray-400">Name:</span>
                  <span class="font-medium">{{ selectedStave.name }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Type:</span>
                  <UBadge :color="getDataSourceTypeColor(selectedStave.data_source_type)" variant="subtle">
                    {{ selectedStave.data_source_type.toUpperCase() }}
                  </UBadge>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Status:</span>
                  <UBadge :color="selectedStave.is_active ? 'green' : 'gray'" variant="subtle">
                    {{ selectedStave.is_active ? 'Active' : 'Inactive' }}
                  </UBadge>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Created:</span>
                  <span class="font-medium">{{ formatDate(selectedStave.created_at) }}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 class="font-semibold mb-2">Connection Configuration</h4>
              <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <pre class="text-sm text-gray-700 dark:text-gray-300">{{ JSON.stringify(selectedStave.connection_config, null, 2) }}</pre>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div v-if="selectedStave.description">
            <h4 class="font-semibold mb-2">Description</h4>
            <p class="text-gray-600 dark:text-gray-400">{{ selectedStave.description }}</p>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <UButton
              color="green"
              icon="i-heroicons-arrow-path"
              @click="testConnection(selectedStave)"
            >
              Test Connection
            </UButton>
            <UButton
              color="blue"
              variant="outline"
              icon="i-heroicons-pencil"
              @click="editStave(selectedStave)"
            >
              Edit Source
            </UButton>
            <UButton
              color="red"
              variant="outline"
              icon="i-heroicons-trash"
              @click="deleteStave(selectedStave)"
            >
              Delete Source
            </UButton>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useStaves } from '~/composables/useStaves'

// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

const {
  staves,
  isLoading,
  error,
  fetchStaves,
  createStave,
  updateStave,
  deleteStave: deleteStaveService,
  testConnection: testConnectionService
} = useStaves()

const showDetailsModal = ref(false)
const showAddModal = ref(false)
const selectedStave = ref(null)

const staveColumns = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'data_source_type', label: 'Type' },
  { key: 'is_active', label: 'Status' },
  { key: 'created_at', label: 'Created' },
  { key: 'actions', label: 'Actions' }
]

// Helper functions
function getDataSourceTypeColor(type: string) {
  const colors: Record<string, string> = {
    postgres: 'blue',
    mysql: 'orange',
    mongodb: 'green',
    sqlite: 'purple',
    redis: 'red',
    snowflake: 'cyan',
    bigquery: 'yellow'
  }
  return colors[type] || 'gray'
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

// Actions
async function refreshStaves() {
  await fetchStaves()
}

function viewStaveDetails(stave: any) {
  selectedStave.value = stave
  showDetailsModal.value = true
}

function testConnection(stave: any) {
  console.log(`Testing connection for stave: ${stave.name}`)
  testConnectionService(stave.id)
}

function editStave(stave: any) {
  console.log(`Editing stave: ${stave.name}`)
  // TODO: Implement stave editing
}

function deleteStave(stave: any) {
  console.log(`Deleting stave: ${stave.name}`)
  deleteStaveService(stave.id)
}

// Load data on mount
onMounted(() => {
  refreshStaves()
})

// Set page meta
useHead({
  title: 'Data Sources - DataMetronome'
})
</script>
