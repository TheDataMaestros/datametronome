<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">ML Anomaly Detection</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Machine learning powered anomaly detection using advanced algorithms.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <UButton
          color="primary"
          variant="outline"
          icon="i-heroicons-cog-6-tooth"
          @click="showMLConfig = !showMLConfig"
        >
          ML Config
        </UButton>
        <UButton
          color="primary"
          icon="i-heroicons-play"
          @click="runMLDetection"
          :loading="isRunningML"
        >
          Run ML Detection
        </UButton>
      </div>
    </div>

    <!-- ML Configuration Panel -->
    <UCard v-if="showMLConfig">
      <template #header>
        <h3 class="text-lg font-semibold">Machine Learning Configuration</h3>
      </template>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-4">
          <UFormGroup label="Algorithm">
            <USelect v-model="mlConfig.algorithm" :options="algorithmOptions" />
          </UFormGroup>
          <UFormGroup label="Contamination Factor">
            <UInput v-model="mlConfig.contamination" type="number" step="0.01" min="0" max="0.5" />
          </UFormGroup>
          <UFormGroup label="Random State">
            <UInput v-model="mlConfig.randomState" type="number" />
          </UFormGroup>
        </div>
        <div class="space-y-4">
          <UFormGroup label="Number of Estimators">
            <UInput v-model="mlConfig.nEstimators" type="number" min="10" max="1000" />
          </UFormGroup>
          <UFormGroup label="Max Features">
            <UInput v-model="mlConfig.maxFeatures" type="number" min="1" />
          </UFormGroup>
          <UFormGroup label="Bootstrap">
            <UToggle v-model="mlConfig.bootstrap" />
          </UFormGroup>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <UButton color="gray" variant="outline" @click="resetMLConfig"> Reset </UButton>
          <UButton color="primary" @click="saveMLConfig"> Save Configuration </UButton>
        </div>
      </template>
    </UCard>

    <!-- ML Results Summary -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <UCard class="gradient-primary text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Records Analyzed</p>
            <p class="text-3xl font-bold">{{ mlResults.totalRecords }}</p>
            <p class="text-sm opacity-90">Last run: {{ formatTimeAgo(mlResults.lastRun) }}</p>
          </div>
          <Icon name="i-heroicons-chart-bar" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-error text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Anomalies Detected</p>
            <p class="text-3xl font-bold">{{ mlResults.anomaliesDetected }}</p>
            <p class="text-sm opacity-90">{{ mlResults.detectionRate }}% detection rate</p>
          </div>
          <Icon name="i-heroicons-exclamation-triangle" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="gradient-success text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Model Confidence</p>
            <p class="text-3xl font-bold">{{ mlResults.modelConfidence }}%</p>
            <p class="text-sm opacity-90">High confidence</p>
          </div>
          <Icon name="i-heroicons-cpu-chip" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>

      <UCard class="bg-purple-500 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm opacity-90">Training Accuracy</p>
            <p class="text-3xl font-bold">{{ mlResults.trainingAccuracy }}%</p>
            <p class="text-sm opacity-90">Based on {{ mlResults.trainingRecords }} samples</p>
          </div>
          <Icon name="i-heroicons-academic-cap" class="w-8 h-8 opacity-80" />
        </div>
      </UCard>
    </div>

    <!-- ML Visualization -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Anomaly Distribution Chart -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Anomaly Distribution</h3>
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="refreshDistributionChart"
            />
          </div>
        </template>
        <div class="chart-container">
          <div class="flex items-center justify-center h-full text-gray-500">
            <div class="text-center">
              <Icon name="i-heroicons-chart-pie" class="w-12 h-12 mx-auto mb-2" />
              <p>ML anomaly distribution chart coming soon</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Model Performance Chart -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Model Performance Over Time</h3>
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="refreshPerformanceChart"
            />
          </div>
        </template>
        <div class="chart-container">
          <div class="flex items-center justify-center h-full text-gray-500">
            <div class="text-center">
              <Icon name="i-heroicons-chart-bar" class="w-12 h-12 mx-auto mb-2" />
              <p>Model performance chart coming soon</p>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- ML Anomalies Table -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">ML Detected Anomalies</h3>
          <div class="flex items-center gap-2">
            <UButton
              color="green"
              variant="outline"
              size="sm"
              icon="i-heroicons-check"
              @click="validateAllAnomalies"
            >
              Validate All
            </UButton>
            <UButton
              color="primary"
              variant="outline"
              size="sm"
              icon="i-heroicons-arrow-down-tray"
              @click="exportMLResults"
            >
              Export Results
            </UButton>
          </div>
        </div>
      </template>

      <UTable :rows="mlAnomalies" :columns="mlAnomalyColumns" class="w-full">
        <template #confidence-data="{ row }">
          <div class="flex items-center gap-2">
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="bg-blue-600 h-2 rounded-full"
                :style="{ width: `${row.confidence}%` }"
              ></div>
            </div>
            <span class="text-sm font-medium">{{ row.confidence }}%</span>
          </div>
        </template>

        <template #severity-data="{ row }">
          <UBadge :color="getMLSeverityColor(row.severity)" variant="solid">
            {{ row.severity }}
          </UBadge>
        </template>

        <template #detected-data="{ row }">
          {{ formatTimeAgo(row.detected) }}
        </template>

        <template #actions-data="{ row }">
          <div class="flex items-center gap-2">
            <UButton
              color="blue"
              variant="ghost"
              size="sm"
              icon="i-heroicons-eye"
              @click="viewMLAnomalyDetails(row)"
            />
            <UButton
              color="green"
              variant="ghost"
              size="sm"
              icon="i-heroicons-check"
              @click="validateMLAnomaly(row.id)"
            />
            <UButton
              color="red"
              variant="ghost"
              size="sm"
              icon="i-heroicons-x-mark"
              @click="rejectMLAnomaly(row.id)"
            />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- ML Anomaly Details Modal -->
    <UModal v-model="showMLAnomalyModal" :ui="{ width: 'w-full sm:max-w-4xl' }">
      <UCard v-if="selectedMLAnomaly">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">ML Anomaly Analysis</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showMLAnomalyModal = false"
            />
          </div>
        </template>

        <div class="space-y-6">
          <!-- ML Analysis -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 class="font-semibold mb-2">ML Analysis</h4>
              <div class="space-y-2">
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Confidence Score:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.confidence }}%</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Anomaly Score:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.anomalyScore }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Algorithm Used:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.algorithm }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Feature Importance:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.featureImportance }}%</span>
                </div>
              </div>
            </div>

            <div>
              <h4 class="font-semibold mb-2">Data Context</h4>
              <div class="space-y-2">
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Table:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.table }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Record ID:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.recordId }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Detected:</span>
                  <span class="font-medium">{{ formatTimeAgo(selectedMLAnomaly.detected) }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600 dark:text-gray-400">Source:</span>
                  <span class="font-medium">{{ selectedMLAnomaly.source }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature Analysis -->
          <div>
            <h4 class="font-semibold mb-2">Feature Analysis</h4>
            <div class="space-y-2">
              <div
                v-for="feature in selectedMLAnomaly.features"
                :key="feature.name"
                class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div>
                  <span class="font-medium">{{ feature.name }}</span>
                  <p class="text-sm text-gray-600 dark:text-gray-400">{{ feature.description }}</p>
                </div>
                <div class="text-right">
                  <span class="font-medium">{{ feature.value }}</span>
                  <p class="text-sm text-gray-600 dark:text-gray-400">
                    {{ feature.contribution }}% contribution
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <UButton
              color="green"
              icon="i-heroicons-check"
              @click="validateMLAnomaly(selectedMLAnomaly.id)"
            >
              Validate Anomaly
            </UButton>
            <UButton
              color="blue"
              variant="outline"
              icon="i-heroicons-arrow-path"
              @click="retrainModel(selectedMLAnomaly.id)"
            >
              Retrain Model
            </UButton>
            <UButton
              color="red"
              variant="outline"
              icon="i-heroicons-x-mark"
              @click="rejectMLAnomaly(selectedMLAnomaly.id)"
            >
              Reject
            </UButton>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

const showMLConfig = ref(false)
const isRunningML = ref(false)
const showMLAnomalyModal = ref(false)
const selectedMLAnomaly = ref(null)

// ML Configuration
const mlConfig = ref({
  algorithm: 'isolation_forest',
  contamination: 0.1,
  randomState: 42,
  nEstimators: 100,
  maxFeatures: 'auto',
  bootstrap: true,
})

const algorithmOptions = [
  { label: 'Isolation Forest', value: 'isolation_forest' },
  { label: 'One-Class SVM', value: 'one_class_svm' },
  { label: 'Local Outlier Factor', value: 'lof' },
  { label: 'Elliptic Envelope', value: 'elliptic_envelope' },
]

// ML Results
const mlResults = ref({
  totalRecords: 1500,
  anomaliesDetected: 7,
  detectionRate: 0.47,
  modelConfidence: 94.2,
  trainingAccuracy: 96.8,
  trainingRecords: 10000,
  lastRun: new Date(Date.now() - 1 * 60 * 60 * 1000),
})

// ML Anomalies data
const mlAnomalies = ref([
  {
    id: 1,
    table: 'users',
    recordId: 'user_12345',
    confidence: 94,
    anomalyScore: 0.87,
    severity: 'high',
    detected: new Date(Date.now() - 2 * 60 * 60 * 1000),
    source: 'Production Database',
    algorithm: 'Isolation Forest',
    featureImportance: 85,
    features: [
      { name: 'age', value: 150, description: 'Age value', contribution: 45 },
      { name: 'income', value: 500000, description: 'Annual income', contribution: 30 },
      { name: 'activity_score', value: 0.02, description: 'User activity score', contribution: 25 },
    ],
  },
  {
    id: 2,
    table: 'orders',
    recordId: 'order_67890',
    confidence: 89,
    anomalyScore: 0.82,
    severity: 'medium',
    detected: new Date(Date.now() - 1 * 60 * 60 * 1000),
    source: 'Production Database',
    algorithm: 'Isolation Forest',
    featureImportance: 72,
    features: [
      { name: 'amount', value: 99999, description: 'Order amount', contribution: 50 },
      { name: 'quantity', value: 1, description: 'Item quantity', contribution: 22 },
    ],
  },
])

const mlAnomalyColumns = [
  { key: 'table', label: 'Table' },
  { key: 'recordId', label: 'Record ID' },
  { key: 'confidence', label: 'Confidence' },
  { key: 'severity', label: 'Severity' },
  { key: 'detected', label: 'Detected' },
  { key: 'source', label: 'Source' },
  { key: 'actions', label: 'Actions' },
]

// Helper functions
function getMLSeverityColor(severity: string) {
  const colors: Record<string, string> = {
    high: 'red',
    medium: 'yellow',
    low: 'blue',
  }
  return colors[severity] || 'gray'
}

function formatTimeAgo(date: Date) {
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

// Actions
async function runMLDetection() {
  isRunningML.value = true
  try {
    // Simulate ML detection
    await new Promise((resolve) => setTimeout(resolve, 3000))
    // Refresh ML results
    await refreshMLResults()
  } finally {
    isRunningML.value = false
  }
}

async function refreshMLResults() {
  // Simulate API call to refresh ML results
  await new Promise((resolve) => setTimeout(resolve, 500))
}

async function refreshDistributionChart() {
  await new Promise((resolve) => setTimeout(resolve, 500))
}

async function refreshPerformanceChart() {
  await new Promise((resolve) => setTimeout(resolve, 500))
}

function resetMLConfig() {
  mlConfig.value = {
    algorithm: 'isolation_forest',
    contamination: 0.1,
    randomState: 42,
    nEstimators: 100,
    maxFeatures: 'auto',
    bootstrap: true,
  }
}

function saveMLConfig() {
  console.log('Saving ML configuration:', mlConfig.value)
  showMLConfig.value = false
}

function viewMLAnomalyDetails(anomaly: any) {
  selectedMLAnomaly.value = anomaly
  showMLAnomalyModal.value = true
}

function validateMLAnomaly(anomalyId: number) {
  const anomaly = mlAnomalies.value.find((a) => a.id === anomalyId)
  if (anomaly) {
    // Mark as validated
    console.log(`Validating ML anomaly ${anomalyId}`)
  }
  showMLAnomalyModal.value = false
}

function rejectMLAnomaly(anomalyId: number) {
  const anomaly = mlAnomalies.value.find((a) => a.id === anomalyId)
  if (anomaly) {
    // Remove from list
    const index = mlAnomalies.value.findIndex((a) => a.id === anomalyId)
    mlAnomalies.value.splice(index, 1)
  }
  showMLAnomalyModal.value = false
}

function validateAllAnomalies() {
  console.log('Validating all ML anomalies...')
}

function exportMLResults() {
  console.log('Exporting ML results...')
}

function retrainModel(anomalyId: number) {
  console.log(`Retraining model based on anomaly ${anomalyId}`)
}

// Set page meta
useHead({
  title: 'ML Anomalies - DataMetronome',
})
</script>
