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

            <!-- PostgreSQL and Redshift take the same connection fields.
                 Redshift adds sslmode, since clusters refuse plaintext. -->
            <template
              v-if="['postgres', 'redshift'].includes(newStaveForm.data_source_type)"
            >
              <UFormGroup label="Host" name="host" required>
                <UInput
                  v-model="connectionFields.host"
                  :placeholder="
                    newStaveForm.data_source_type === 'redshift'
                      ? 'my-cluster.abc123.eu-west-1.redshift.amazonaws.com'
                      : 'localhost'
                  "
                />
              </UFormGroup>
              <UFormGroup label="Port" name="port">
                <UInput
                  v-model.number="connectionFields.port"
                  type="number"
                  :placeholder="newStaveForm.data_source_type === 'redshift' ? '5439' : '5432'"
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
              <UFormGroup
                v-if="newStaveForm.data_source_type === 'redshift'"
                label="SSL mode"
                name="sslmode"
              >
                <USelect v-model="connectionFields.sslmode" :options="sslModes" />
              </UFormGroup>
              <UFormGroup
                v-else
                label="SSL mode"
                name="ssl"
              >
                <USelect v-model="connectionFields.ssl" :options="pgSslModes" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  RDS and Aurora instances with rds.force_ssl=1 need "require".
                </p>
              </UFormGroup>
            </template>

            <!-- S3: files become tables, one per line -->
            <template v-else-if="newStaveForm.data_source_type === 's3'">
              <UFormGroup label="Bucket" name="bucket" required>
                <UInput v-model="connectionFields.bucket" placeholder="analytics-prod" />
              </UFormGroup>
              <UFormGroup label="Region" name="region" required>
                <UInput v-model="connectionFields.region" placeholder="eu-west-1" />
              </UFormGroup>

              <UFormGroup label="Tables" name="tables" required>
                <UTextarea
                  v-model="connectionFields.tables"
                  :rows="4"
                  placeholder="users = users/*.parquet&#10;orders = orders/dt=*/*.parquet&#10;signups = raw/signups.csv.gz"
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  One per line, <code>name = path</code>. The name is what checks
                  refer to. Parquet, CSV and JSON are detected by extension.
                </p>
              </UFormGroup>

              <UFormGroup label="Access Key ID" name="access_key_id">
                <UInput v-model="connectionFields.access_key_id" placeholder="optional" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Leave both key fields empty to use the instance role or the
                  AWS environment. Prefer that: no long-lived key is stored.
                </p>
              </UFormGroup>
              <UFormGroup label="Secret Access Key" name="secret_access_key">
                <UInput
                  v-model="connectionFields.secret_access_key"
                  type="password"
                  placeholder="optional, stored encrypted"
                />
              </UFormGroup>
              <UFormGroup label="Endpoint URL" name="endpoint_url">
                <UInput
                  v-model="connectionFields.endpoint_url"
                  placeholder="optional, e.g. http://minio:9000"
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  For MinIO or another S3-compatible store.
                </p>
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

            <!-- dbt (read-only: reads manifest/run_results artifacts) -->
            <template v-else-if="newStaveForm.data_source_type === 'dbt'">
              <UFormGroup label="Mode" name="mode" required>
                <USelect v-model="connectionFields.mode" :options="dbtModes" />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Read artifacts from a local dbt project, or pull them from a dbt Cloud job run
                </p>
              </UFormGroup>

              <template v-if="connectionFields.mode === 'cloud'">
                <UFormGroup label="API Token" name="api_token" required>
                  <UInput
                    v-model="connectionFields.api_token"
                    type="password"
                    placeholder="dbtc_..."
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    dbt Cloud service token. Stored encrypted.
                  </p>
                </UFormGroup>
                <UFormGroup label="Account ID" name="account_id" required>
                  <UInput v-model="connectionFields.account_id" placeholder="12345" />
                </UFormGroup>
                <UFormGroup label="Job ID" name="job_id" required>
                  <UInput v-model="connectionFields.job_id" placeholder="67890" />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Artifacts are read from this job's most recent run
                  </p>
                </UFormGroup>
                <UFormGroup label="Base URL" name="base_url">
                  <UInput
                    v-model="connectionFields.base_url"
                    placeholder="https://cloud.getdbt.com/api/v2"
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Override for single-tenant or EU dbt Cloud instances
                  </p>
                </UFormGroup>
              </template>

              <template v-else>
                <UFormGroup label="Project Path" name="project_path" required>
                  <UInput v-model="connectionFields.project_path" placeholder="/path/to/dbt" />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Root of your dbt project, readable by the DataMetronome server
                  </p>
                </UFormGroup>
                <UFormGroup label="Target Path" name="target_path">
                  <UInput v-model="connectionFields.target_path" placeholder="target" />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Directory holding manifest.json and run_results.json — defaults to
                    <code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">target</code>
                  </p>
                </UFormGroup>
              </template>
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
import { parseS3Tables } from '~/services/staves'

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
  { label: 'Amazon Redshift', value: 'redshift' },
  { label: 'Amazon S3', value: 's3' },
  { label: 'SQLite', value: 'sqlite' },
  { label: 'BigQuery', value: 'bigquery' },
  { label: 'dbt', value: 'dbt' },
]

// psycopg's sslmode values. Redshift clusters refuse plaintext, so the
// default is require rather than prefer.
const sslModes = [
  { label: 'require', value: 'require' },
  { label: 'verify-ca', value: 'verify-ca' },
  { label: 'verify-full', value: 'verify-full' },
]

// asyncpg's ssl values for plain PostgreSQL. Empty leaves negotiation alone.
const pgSslModes = [
  { label: 'default (negotiate)', value: '' },
  { label: 'require', value: 'require' },
  { label: 'verify-full', value: 'verify-full' },
]

const dbtModes = [
  { label: 'Local artifacts', value: 'local' },
  { label: 'dbt Cloud', value: 'cloud' },
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

function resetConnectionFields(type?: string) {
  // Reset connection fields when data source type changes. The select passes
  // the new type in, so this does not depend on v-model having applied yet.
  const next = type ?? newStaveForm.value.data_source_type
  if (next === 'dbt') {
    connectionFields.value = { mode: 'local' }
  } else if (next === 'redshift') {
    // Redshift listens on 5439 and refuses plaintext connections.
    connectionFields.value = { port: 5439, sslmode: 'require' }
  } else if (next === 's3') {
    connectionFields.value = { region: 'eu-west-1', tables: '' }
  } else {
    connectionFields.value = {}
  }
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
    redshift: 'red',
    s3: 'green',
    sqlite: 'purple',
    bigquery: 'yellow',
    dbt: 'orange',
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

  if (type === 'postgres' || type === 'redshift') {
    config.host = fields.host
    if (fields.port) config.port = Number(fields.port)
    config.database = fields.database
    config.user = fields.user
    if (fields.password) config.password = fields.password
    // psycopg spells it sslmode, asyncpg spells it ssl.
    if (type === 'redshift') {
      config.sslmode = fields.sslmode || 'require'
    } else if (fields.ssl) {
      config.ssl = fields.ssl
    }
  } else if (type === 's3') {
    config.bucket = fields.bucket
    config.region = fields.region
    const parsed = parseS3Tables(fields.tables)
    if ('tables' in parsed) config.tables = parsed.tables
    if (fields.access_key_id) config.access_key_id = fields.access_key_id
    if (fields.secret_access_key) config.secret_access_key = fields.secret_access_key
    if (fields.endpoint_url) config.endpoint_url = fields.endpoint_url
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
  } else if (type === 'dbt') {
    config.mode = fields.mode || 'local'
    if (config.mode === 'cloud') {
      config.api_token = fields.api_token
      config.account_id = fields.account_id
      config.job_id = fields.job_id
      if (fields.base_url) config.base_url = fields.base_url
    } else {
      config.project_path = fields.project_path
      if (fields.target_path) config.target_path = fields.target_path
    }
        }

  // Remove undefined/null values
  return Object.fromEntries(
    Object.entries(config).filter(([_, v]) => v !== undefined && v !== null && v !== ''),
  )
}

function validateConnectionConfig(): string | null {
  const type = newStaveForm.value.data_source_type
  const fields = connectionFields.value

  if (type === 'postgres' || type === 'redshift') {
    if (!fields.host) return 'Host is required'
    if (!fields.database) return 'Database is required'
    if (!fields.user) return 'Username is required'
  } else if (type === 's3') {
    if (!fields.bucket) return 'Bucket is required'
    if (!fields.region) return 'Region is required'
    const parsed = parseS3Tables(fields.tables)
    if ('error' in parsed) return parsed.error
  } else if (type === 'sqlite') {
    if (!fields.path) return 'Database path is required'
  } else if (type === 'bigquery') {
    if (!fields.project_id) return 'Project ID is required'
    if (!fields.credentials_json && !fields.credentials_path) {
      return 'Please upload a credentials JSON file or paste the JSON content'
    }
  } else if (type === 'dbt') {
    // Mirrors DbtReadonlyPulse, which raises on these same missing fields
    if ((fields.mode || 'local') === 'cloud') {
      if (!fields.api_token) return 'API token is required for dbt Cloud mode'
      if (!fields.account_id) return 'Account ID is required for dbt Cloud mode'
      if (!fields.job_id) return 'Job ID is required for dbt Cloud mode'
    } else if (!fields.project_path) {
      return 'Project path is required for local mode'
    }
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
