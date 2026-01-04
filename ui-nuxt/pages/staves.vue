<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Data Sources</h1>
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

      <!-- Error State -->
      <div
        v-if="error"
        class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4"
      >
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0">
            <span class="text-2xl">⚠️</span>
          </div>
          <div class="flex-1">
            <h4 class="font-semibold text-red-800 dark:text-red-200 mb-1">
              Error Loading Data Sources
            </h4>
            <p class="text-sm text-red-700 dark:text-red-300 mb-3">{{ error }}</p>
            <UButton
              color="red"
              variant="outline"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="refreshStaves"
            >
              Retry
            </UButton>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!isLoading && staves.length === 0" class="text-center py-12">
        <p class="text-gray-500 dark:text-gray-400 mb-4">No data sources found</p>
        <UButton
          color="primary"
          variant="outline"
          icon="i-heroicons-plus"
          @click="showAddModal = true"
        >
          Create Your First Data Source
        </UButton>
      </div>

      <!-- Staves Table -->
      <UTable v-else :rows="staves" :columns="staveColumns" class="w-full">
        <template #data_source_type-data="{ row }">
          <UBadge :color="getDataSourceTypeColor(row.data_source_type)" variant="subtle">
            {{ row.data_source_type.toUpperCase() }}
          </UBadge>
        </template>

        <template #is_active-data="{ row }">
          <UBadge :color="row.is_active ? 'green' : 'gray'" variant="subtle">
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
              :loading="testingConnection === row.id"
              :disabled="testingConnection !== null"
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

    <!-- Add Stave Modal -->
    <UModal v-model="showAddModal" :ui="{ width: 'w-full sm:max-w-2xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Create New Data Source</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showAddModal = false"
            />
          </div>
        </template>

        <form @submit.prevent="handleCreateStave" class="space-y-4">
          <UFormGroup label="Name" name="name" required>
            <UInput v-model="newStaveForm.name" placeholder="e.g., Production Database" />
          </UFormGroup>

          <UFormGroup label="Description" name="description">
            <UTextarea
              v-model="newStaveForm.description"
              placeholder="Optional description of the data source"
              :rows="3"
            />
          </UFormGroup>

          <UFormGroup label="Data Source Type" name="data_source_type" required>
            <USelect
              v-model="newStaveForm.data_source_type"
              :options="dataSourceTypes"
              placeholder="Select data source type"
              @update:model-value="resetConnectionFields"
            />
          </UFormGroup>

          <!-- Dynamic Connection Fields based on Data Source Type -->
          <div
            v-if="newStaveForm.data_source_type"
            class="space-y-4 border-t border-gray-200 dark:border-gray-700 pt-4"
          >
            <h4 class="font-semibold text-sm">Connection Settings</h4>

            <!-- PostgreSQL / MySQL -->
            <template v-if="['postgres', 'mysql'].includes(newStaveForm.data_source_type)">
              <UFormGroup label="Host" name="host" required>
                <UInput v-model="connectionFields.host" placeholder="localhost" />
              </UFormGroup>
              <UFormGroup label="Port" name="port">
                <UInput
                  v-model.number="connectionFields.port"
                  type="number"
                  :placeholder="newStaveForm.data_source_type === 'postgres' ? '5432' : '3306'"
                />
              </UFormGroup>
              <UFormGroup label="Database" name="database" required>
                <UInput v-model="connectionFields.database" placeholder="mydb" />
              </UFormGroup>
              <UFormGroup label="Username" name="user" required>
                <UInput v-model="connectionFields.user" placeholder="username" />
              </UFormGroup>
              <UFormGroup label="Password" name="password">
                <UInput
                  v-model="connectionFields.password"
                  type="password"
                  placeholder="password (optional)"
                />
              </UFormGroup>
            </template>

            <!-- SQLite -->
            <template v-else-if="newStaveForm.data_source_type === 'sqlite'">
              <UFormGroup label="Database Path" name="path" required>
                <UInput v-model="connectionFields.path" placeholder="/path/to/database.db" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Full path to your SQLite database file
                </p>
              </UFormGroup>
            </template>

            <!-- BigQuery -->
            <template v-else-if="newStaveForm.data_source_type === 'bigquery'">
              <UFormGroup label="Project ID" name="project_id" required>
                <UInput v-model="connectionFields.project_id" placeholder="my-gcp-project" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Your Google Cloud Platform project ID
                </p>
              </UFormGroup>

              <UFormGroup label="Service Account Credentials" name="credentials" required>
                <div class="space-y-3">
                  <!-- File Upload Option -->
                  <div>
                    <label class="block text-sm font-medium mb-2">Upload JSON File</label>
                    <input
                      type="file"
                      accept=".json,application/json"
                      @change="handleCredentialsFileUpload"
                      class="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 dark:file:bg-primary-900 dark:file:text-primary-300 dark:hover:file:bg-primary-800 cursor-pointer"
                    />
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Upload your GCP service account JSON key file
                    </p>
                  </div>

                  <!-- Or Divider -->
                  <div class="relative">
                    <div class="absolute inset-0 flex items-center">
                      <div class="w-full border-t border-gray-300 dark:border-gray-600"></div>
                    </div>
                    <div class="relative flex justify-center text-xs uppercase">
                      <span class="bg-white dark:bg-gray-900 px-2 text-gray-500 dark:text-gray-400"
                        >Or</span
                      >
                    </div>
                  </div>

                  <!-- JSON Paste Option -->
                  <div>
                    <label class="block text-sm font-medium mb-2">Paste JSON Credentials</label>
                    <UTextarea
                      v-model="connectionFields.credentials_json_text"
                      placeholder='{"type": "service_account", "project_id": "...", "private_key": "...", ...}'
                      :rows="8"
                      class="font-mono text-sm"
                      @blur="parseCredentialsJson"
                    />
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Paste the contents of your service account JSON file
                    </p>
                  </div>

                  <!-- Show uploaded/pasted indicator -->
                  <div
                    v-if="connectionFields.credentials_json"
                    class="p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
                  >
                    <p class="text-xs text-green-700 dark:text-green-300 flex items-center gap-1">
                      <span class="text-green-600 dark:text-green-400">✓</span>
                      Credentials loaded successfully
                    </p>
                  </div>
                </div>
              </UFormGroup>

              <UFormGroup label="Dataset" name="dataset">
                <UInput
                  v-model="connectionFields.dataset"
                  placeholder="analytics or bigquery-public-data.samples"
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Default dataset name (optional). For public datasets, use format
                  <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded"
                    >PROJECT.DATASET</code
                  >
                  (e.g.,
                  <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded"
                    >bigquery-public-data.samples</code
                  >)
                </p>
              </UFormGroup>
              <UFormGroup label="Location" name="location">
                <UInput v-model="connectionFields.location" placeholder="US" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  BigQuery location (US, EU, etc.) - defaults to US
                </p>
              </UFormGroup>
            </template>

            <!-- MongoDB -->
            <template v-else-if="newStaveForm.data_source_type === 'mongodb'">
              <UFormGroup label="Connection URI" name="uri" required>
                <UInput
                  v-model="connectionFields.uri"
                  placeholder="mongodb://user:pass@host:27017/"
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Full MongoDB connection URI
                </p>
              </UFormGroup>
              <UFormGroup label="Database" name="database" required>
                <UInput v-model="connectionFields.database" placeholder="mydb" />
              </UFormGroup>
            </template>

            <!-- Redis -->
            <template v-else-if="newStaveForm.data_source_type === 'redis'">
              <UFormGroup label="Host" name="host" required>
                <UInput v-model="connectionFields.host" placeholder="localhost" />
              </UFormGroup>
              <UFormGroup label="Port" name="port">
                <UInput v-model.number="connectionFields.port" type="number" placeholder="6379" />
              </UFormGroup>
              <UFormGroup label="Database Number" name="db">
                <UInput v-model.number="connectionFields.db" type="number" placeholder="0" />
              </UFormGroup>
              <UFormGroup label="Password" name="password">
                <UInput
                  v-model="connectionFields.password"
                  type="password"
                  placeholder="password (optional)"
                />
              </UFormGroup>
            </template>

            <!-- Snowflake -->
            <template v-else-if="newStaveForm.data_source_type === 'snowflake'">
              <UFormGroup label="Account" name="account" required>
                <UInput v-model="connectionFields.account" placeholder="abc12345.us-east-1" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Your Snowflake account identifier
                </p>
              </UFormGroup>
              <UFormGroup label="Username" name="user" required>
                <UInput v-model="connectionFields.user" placeholder="username" />
              </UFormGroup>
              <UFormGroup label="Password" name="password" required>
                <UInput
                  v-model="connectionFields.password"
                  type="password"
                  placeholder="password"
                />
              </UFormGroup>
              <UFormGroup label="Warehouse" name="warehouse" required>
                <UInput v-model="connectionFields.warehouse" placeholder="COMPUTE_WH" />
              </UFormGroup>
              <UFormGroup label="Database" name="database" required>
                <UInput v-model="connectionFields.database" placeholder="ANALYTICS" />
              </UFormGroup>
              <UFormGroup label="Schema" name="schema">
                <UInput v-model="connectionFields.schema" placeholder="PUBLIC" />
              </UFormGroup>
              <UFormGroup label="Role" name="role">
                <UInput v-model="connectionFields.role" placeholder="MONITOR_ROLE" />
              </UFormGroup>
            </template>
          </div>

          <UFormGroup label="Active" name="is_active">
            <UToggle v-model="newStaveForm.is_active" />
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Whether this data source should be actively monitored
            </p>
          </UFormGroup>

          <div
            v-if="formError"
            class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
          >
            <p class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          </div>

          <div
            class="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700"
          >
            <UButton color="gray" variant="outline" @click="showAddModal = false"> Cancel </UButton>
            <UButton type="submit" color="primary" :loading="isLoading">
              Create Data Source
            </UButton>
          </div>
        </form>
      </UCard>
    </UModal>

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
                  <UBadge
                    :color="getDataSourceTypeColor(selectedStave.data_source_type)"
                    variant="subtle"
                  >
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
                <pre class="text-sm text-gray-700 dark:text-gray-300">{{
                  JSON.stringify(selectedStave.connection_config, null, 2)
                }}</pre>
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
              :loading="testingConnection === selectedStave?.id"
              :disabled="testingConnection !== null"
              @click="testConnection(selectedStave)"
            >
              Test Connection
            </UButton>

            <!-- Connection Test Result -->
            <div
              v-if="connectionTestResult && selectedStave && testingConnection === null"
              class="mt-4 p-4 rounded-lg"
              :class="
                connectionTestResult.success
                  ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              "
            >
              <div class="flex items-start gap-2">
                <span class="text-lg">{{ connectionTestResult.success ? '✓' : '✗' }}</span>
                <div class="flex-1">
                  <p
                    class="font-semibold"
                    :class="
                      connectionTestResult.success
                        ? 'text-green-800 dark:text-green-200'
                        : 'text-red-800 dark:text-red-200'
                    "
                  >
                    {{
                      connectionTestResult.success ? 'Connection Successful' : 'Connection Failed'
                    }}
                  </p>
                  <p
                    class="text-sm mt-1"
                    :class="
                      connectionTestResult.success
                        ? 'text-green-700 dark:text-green-300'
                        : 'text-red-700 dark:text-red-300'
                    "
                  >
                    {{ connectionTestResult.message }}
                  </p>
                  <div
                    v-if="
                      connectionTestResult.metadata &&
                      Object.keys(connectionTestResult.metadata).length > 0
                    "
                    class="mt-2 text-xs"
                    :class="
                      connectionTestResult.success
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    "
                  >
                    <details class="cursor-pointer">
                      <summary class="font-semibold">Details</summary>
                      <pre
                        class="mt-2 p-2 bg-white dark:bg-gray-800 rounded text-xs overflow-auto"
                        >{{ JSON.stringify(connectionTestResult.metadata, null, 2) }}</pre
                      >
                    </details>
                  </div>
                </div>
                <UButton
                  color="gray"
                  variant="ghost"
                  size="xs"
                  icon="i-heroicons-x-mark"
                  @click="connectionTestResult = null"
                />
              </div>
            </div>
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
  layout: 'dashboard',
})

const {
  staves,
  isLoading,
  error,
  fetchStaves,
  createStave,
  updateStave,
  deleteStave: deleteStaveService,
  testConnection: testConnectionService,
} = useStaves()

const showDetailsModal = ref(false)
const showAddModal = ref(false)
const selectedStave = ref(null)

const dataSourceTypes = [
  { label: 'PostgreSQL', value: 'postgres' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'MongoDB', value: 'mongodb' },
  { label: 'SQLite', value: 'sqlite' },
  { label: 'Redis', value: 'redis' },
  { label: 'Snowflake', value: 'snowflake' },
  { label: 'BigQuery', value: 'bigquery' },
]

const newStaveForm = ref({
  name: '',
  description: '',
  data_source_type: '',
  connection_config: {},
  is_active: true,
})

const connectionFields = ref<Record<string, any>>({})
const formError = ref<string | null>(null)

function resetConnectionFields() {
  // Reset connection fields when data source type changes
  connectionFields.value = {}
}

function handleCredentialsFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  if (!file.name.endsWith('.json')) {
    formError.value = 'Please upload a JSON file'
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const jsonText = e.target?.result as string
      const credentials = JSON.parse(jsonText)

      // Validate it looks like a service account JSON
      if (!credentials.type || credentials.type !== 'service_account') {
        formError.value = 'Invalid service account JSON file'
        return
      }

      connectionFields.value.credentials_json = credentials
      connectionFields.value.credentials_json_text = JSON.stringify(credentials, null, 2)
      formError.value = null
    } catch (err) {
      formError.value = 'Failed to parse JSON file. Please check the file format.'
      console.error('Error parsing credentials file:', err)
    }
  }

  reader.onerror = () => {
    formError.value = 'Failed to read file'
  }

  reader.readAsText(file)
}

function parseCredentialsJson() {
  const jsonText = connectionFields.value.credentials_json_text
  if (!jsonText || !jsonText.trim()) {
    connectionFields.value.credentials_json = null
    return
  }

  try {
    const credentials = JSON.parse(jsonText)

    // Validate it looks like a service account JSON
    if (!credentials.type || credentials.type !== 'service_account') {
      formError.value = 'Invalid service account JSON. Must have type: "service_account"'
      connectionFields.value.credentials_json = null
      return
    }

    connectionFields.value.credentials_json = credentials
    formError.value = null
  } catch (err) {
    formError.value = 'Invalid JSON format. Please check your JSON syntax.'
    connectionFields.value.credentials_json = null
  }
}

const staveColumns = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'data_source_type', label: 'Type' },
  { key: 'is_active', label: 'Status' },
  { key: 'created_at', label: 'Created' },
  { key: 'actions', label: 'Actions' },
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
    bigquery: 'yellow',
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
  connectionTestResult.value = null // Clear previous test result
  showDetailsModal.value = true
}

const testingConnection = ref<string | null>(null)
const connectionTestResult = ref<{ success: boolean; message: string; metadata?: any } | null>(null)

async function testConnection(stave: any) {
  testingConnection.value = stave.id
  connectionTestResult.value = null

  try {
    const result = await testConnectionService(stave.id)
    connectionTestResult.value = result

    // Show notification
    if (result.success) {
      // You might want to use a toast/notification library here
      console.log('✅ Connection test successful:', result.message)
    } else {
      console.error('❌ Connection test failed:', result.message)
    }
  } catch (err) {
    connectionTestResult.value = {
      success: false,
      message: err instanceof Error ? err.message : 'Failed to test connection',
    }
    console.error('Connection test error:', err)
  } finally {
    testingConnection.value = null
  }
}

function editStave(stave: any) {
  console.log(`Editing stave: ${stave.name}`)
  // TODO: Implement stave editing
}

function deleteStave(stave: any) {
  console.log(`Deleting stave: ${stave.name}`)
  deleteStaveService(stave.id)
}

function buildConnectionConfig(): Record<string, any> {
  const type = newStaveForm.value.data_source_type
  const fields = connectionFields.value
  const config: Record<string, any> = {}

  if (['postgres', 'mysql'].includes(type)) {
    config.host = fields.host
    if (fields.port) config.port = Number(fields.port)
    config.database = fields.database
    config.user = fields.user
    if (fields.password) config.password = fields.password
  } else if (type === 'sqlite') {
    config.path = fields.path
  } else if (type === 'bigquery') {
    config.project_id = fields.project_id
    // Use credentials_json if available, otherwise fall back to credentials_path (for backward compatibility)
    if (fields.credentials_json) {
      config.credentials_json = fields.credentials_json
    } else if (fields.credentials_path) {
      config.credentials_path = fields.credentials_path
    }
    if (fields.dataset) config.dataset = fields.dataset
    if (fields.location) config.location = fields.location
  } else if (type === 'mongodb') {
    config.uri = fields.uri
    config.database = fields.database
  } else if (type === 'redis') {
    config.host = fields.host
    if (fields.port) config.port = Number(fields.port)
    if (fields.db !== undefined) config.db = Number(fields.db)
    if (fields.password) config.password = fields.password
  } else if (type === 'snowflake') {
    config.account = fields.account
    config.user = fields.user
    config.password = fields.password
    config.warehouse = fields.warehouse
    config.database = fields.database
    if (fields.schema) config.schema = fields.schema
    if (fields.role) config.role = fields.role
  }

  // Remove undefined/null values
  return Object.fromEntries(
    Object.entries(config).filter(([_, v]) => v !== undefined && v !== null && v !== ''),
  )
}

function validateConnectionConfig(): string | null {
  const type = newStaveForm.value.data_source_type
  const fields = connectionFields.value

  if (['postgres', 'mysql'].includes(type)) {
    if (!fields.host) return 'Host is required'
    if (!fields.database) return 'Database is required'
    if (!fields.user) return 'Username is required'
  } else if (type === 'sqlite') {
    if (!fields.path) return 'Database path is required'
  } else if (type === 'bigquery') {
    if (!fields.project_id) return 'Project ID is required'
    if (!fields.credentials_json && !fields.credentials_path) {
      return 'Please upload a credentials JSON file or paste the JSON content'
    }
  } else if (type === 'mongodb') {
    if (!fields.uri) return 'Connection URI is required'
    if (!fields.database) return 'Database is required'
  } else if (type === 'redis') {
    if (!fields.host) return 'Host is required'
  } else if (type === 'snowflake') {
    if (!fields.account) return 'Account is required'
    if (!fields.user) return 'Username is required'
    if (!fields.password) return 'Password is required'
    if (!fields.warehouse) return 'Warehouse is required'
    if (!fields.database) return 'Database is required'
  }

  return null
}

async function handleCreateStave() {
  formError.value = null

  try {
    // Validate basic fields
    if (!newStaveForm.value.name || !newStaveForm.value.data_source_type) {
      formError.value = 'Name and data source type are required'
      return
    }

    // Validate connection config
    const validationError = validateConnectionConfig()
    if (validationError) {
      formError.value = validationError
      return
    }

    // Build connection config from form fields
    const connectionConfig = buildConnectionConfig()

    // Create the stave
    await createStave({
      name: newStaveForm.value.name,
      description: newStaveForm.value.description || undefined,
      data_source_type: newStaveForm.value.data_source_type,
      connection_config: connectionConfig,
    })

    // Reset form and close modal
    newStaveForm.value = {
      name: '',
      description: '',
      data_source_type: '',
      connection_config: {},
      is_active: true,
    }
    connectionFields.value = {}
    formError.value = null
    showAddModal.value = false

    // Refresh the list
    await refreshStaves()
  } catch (err) {
    console.error('Error creating stave:', err)
    formError.value = err instanceof Error ? err.message : 'Failed to create data source'
  }
}

// Load data on mount
onMounted(() => {
  refreshStaves()
})

// Set page meta
useHead({
  title: 'Data Sources - DataMetronome',
})
</script>
