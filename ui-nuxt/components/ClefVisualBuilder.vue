<template>
  <div class="space-y-6">
    <!-- Visual Builder Header -->
    <div class="text-center">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        🎼 Visual Clef Builder
      </h2>
      <p class="text-gray-600 dark:text-gray-400">
        Build your data quality checks with an intuitive visual interface
      </p>
    </div>

    <!-- Builder Steps -->
    <div class="flex items-center justify-center space-x-4 mb-8">
      <div 
        v-for="(step, index) in steps" 
        :key="index"
        class="flex items-center"
      >
        <div 
          class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
          :class="getStepClass(index)"
        >
          {{ index + 1 }}
        </div>
        <span 
          class="ml-2 text-sm font-medium"
          :class="getStepTextClass(index)"
        >
          {{ step }}
        </span>
        <Icon 
          v-if="index < steps.length - 1"
          name="i-heroicons-chevron-right" 
          class="w-4 h-4 mx-4 text-gray-400"
        />
      </div>
    </div>

    <!-- Step Content -->
    <div class="max-w-4xl mx-auto">
      <!-- Step 1: Choose Clef Type -->
      <div v-if="currentStep === 0" class="space-y-6">
        <h3 class="text-xl font-semibold text-center mb-6">Choose Your Clef Type</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <UCard 
            v-for="template in clefTemplates" 
            :key="template.type"
            class="cursor-pointer hover:shadow-lg transition-all hover:scale-105 group"
            :class="{ 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20': selectedType === template.type }"
            @click="selectType(template.type)"
          >
            <div class="text-center space-y-4">
              <div class="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Icon :name="template.icon" class="w-8 h-8 text-white" />
              </div>
              
              <div>
                <h4 class="font-semibold text-lg">{{ template.name }}</h4>
                <p class="text-sm text-gray-600 dark:text-gray-400 mt-2">{{ template.description }}</p>
              </div>
              
              <div class="flex items-center justify-center space-x-2">
                <UBadge :color="getTierColor(template.tier)" variant="soft">
                  Tier {{ template.tier }}
                </UBadge>
                <UBadge color="gray" variant="soft" size="xs">
                  {{ getTierDescription(template.tier) }}
                </UBadge>
              </div>
              
              <!-- Difficulty indicator -->
              <div class="flex items-center justify-center space-x-1">
                <Icon 
                  v-for="i in template.tier" 
                  :key="i"
                  name="i-heroicons-star-solid" 
                  class="w-4 h-4 text-yellow-400"
                />
                <Icon 
                  v-for="i in (4 - template.tier)" 
                  :key="i"
                  name="i-heroicons-star" 
                  class="w-4 h-4 text-gray-300"
                />
              </div>
            </div>
          </UCard>
        </div>
      </div>

      <!-- Step 2: Configure Clef -->
      <div v-if="currentStep === 1" class="space-y-6">
        <h3 class="text-xl font-semibold text-center mb-6">Configure Your {{ getSelectedTemplate()?.name }}</h3>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <!-- Configuration Form -->
          <div class="space-y-6">
            <UCard>
              <template #header>
                <h4 class="font-semibold">Basic Settings</h4>
              </template>
              
              <div class="space-y-4">
                <UFormGroup label="Clef Name" required>
                  <UInput 
                    v-model="builderConfig.name" 
                    placeholder="e.g., Email Validation Check"
                  />
                </UFormGroup>
                
                <UFormGroup label="Description">
                  <UTextarea 
                    v-model="builderConfig.description" 
                    placeholder="Describe what this clef validates"
                    rows="3"
                  />
                </UFormGroup>
                
                <UFormGroup label="Target Stave" required>
                  <USelect
                    v-model="builderConfig.stave_id"
                    :options="staveOptions"
                    placeholder="Select a data source"
                  />
                </UFormGroup>
              </div>
            </UCard>

            <!-- Type-specific Configuration -->
            <UCard>
              <template #header>
                <h4 class="font-semibold">{{ getSelectedTemplate()?.name }} Configuration</h4>
              </template>
              
              <ClefConfigForm 
                :clef-type="selectedType"
                :config="builderConfig.configuration"
                @update:config="builderConfig.configuration = $event"
              />
            </UCard>
          </div>

          <!-- Preview -->
          <div class="space-y-6">
            <UCard>
              <template #header>
                <h4 class="font-semibold">Preview</h4>
              </template>
              
              <div class="space-y-4">
                <div class="flex items-center space-x-3">
                  <Icon :name="getSelectedTemplate()?.icon" class="w-6 h-6 text-blue-500" />
                  <div>
                    <h5 class="font-medium">{{ builderConfig.name || 'Untitled Clef' }}</h5>
                    <p class="text-sm text-gray-600 dark:text-gray-400">{{ builderConfig.description || 'No description' }}</p>
                  </div>
                </div>
                
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h6 class="font-medium mb-2">Configuration:</h6>
                  <pre class="text-sm text-gray-700 dark:text-gray-300">{{ JSON.stringify(builderConfig.configuration, null, 2) }}</pre>
                </div>
              </div>
            </UCard>

            <!-- Tips -->
            <UCard>
              <template #header>
                <h4 class="font-semibold">💡 Tips</h4>
              </template>
              
              <div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <div v-for="tip in getTips()" :key="tip" class="flex items-start space-x-2">
                  <Icon name="i-heroicons-light-bulb" class="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                  <span>{{ tip }}</span>
                </div>
              </div>
            </UCard>
          </div>
        </div>
      </div>

      <!-- Step 3: Schedule & Thresholds -->
      <div v-if="currentStep === 2" class="space-y-6">
        <h3 class="text-xl font-semibold text-center mb-6">Set Schedule & Thresholds</h3>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <!-- Schedule Configuration -->
          <UCard>
            <template #header>
              <h4 class="font-semibold">⏰ Schedule</h4>
            </template>
            
            <div class="space-y-4">
              <UFormGroup label="Run Frequency">
                <USelect
                  v-model="builderConfig.schedule"
                  :options="scheduleOptions"
                  placeholder="Select frequency"
                />
              </UFormGroup>
              
              <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <div class="flex items-center space-x-2 mb-2">
                  <Icon name="i-heroicons-information-circle" class="w-5 h-5 text-blue-500" />
                  <span class="font-medium text-blue-900 dark:text-blue-100">Schedule Info</span>
                </div>
                <p class="text-sm text-blue-800 dark:text-blue-200">
                  {{ getScheduleDescription(builderConfig.schedule) }}
                </p>
              </div>
            </div>
          </UCard>

          <!-- Severity Thresholds -->
          <UCard>
            <template #header>
              <h4 class="font-semibold">⚠️ Severity Thresholds</h4>
            </template>
            
            <div class="space-y-4">
              <UFormGroup label="Warning Threshold">
                <UInput 
                  v-model="builderConfig.warn" 
                  placeholder="e.g., > 5%"
                />
                <template #help>
                  <span class="text-sm text-gray-500">Triggers a warning when exceeded</span>
                </template>
              </UFormGroup>
              
              <UFormGroup label="Failure Threshold">
                <UInput 
                  v-model="builderConfig.fail" 
                  placeholder="e.g., > 20%"
                />
                <template #help>
                  <span class="text-sm text-gray-500">Triggers a failure when exceeded</span>
                </template>
              </UFormGroup>
              
              <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                <div class="flex items-center space-x-2 mb-2">
                  <Icon name="i-heroicons-exclamation-triangle" class="w-5 h-5 text-yellow-500" />
                  <span class="font-medium text-yellow-900 dark:text-yellow-100">Threshold Examples</span>
                </div>
                <div class="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
                  <div>• Percentage: <code>> 5%</code>, <code>< 1%</code></div>
                  <div>• Count: <code>> 100</code>, <code>< 10</code></div>
                  <div>• Time: <code>> 24h</code>, <code>< 1h</code></div>
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </div>

      <!-- Step 4: Review & Create -->
      <div v-if="currentStep === 3" class="space-y-6">
        <h3 class="text-xl font-semibold text-center mb-6">Review & Create</h3>
        
        <div class="max-w-2xl mx-auto">
          <UCard>
            <template #header>
              <div class="flex items-center space-x-3">
                <Icon :name="getSelectedTemplate()?.icon" class="w-6 h-6 text-blue-500" />
                <h4 class="font-semibold">{{ builderConfig.name }}</h4>
              </div>
            </template>
            
            <div class="space-y-6">
              <!-- Summary -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h5 class="font-medium text-gray-900 dark:text-white mb-2">Details</h5>
                  <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    <div><strong>Type:</strong> {{ getSelectedTemplate()?.name }}</div>
                    <div><strong>Stave:</strong> {{ getStaveName(builderConfig.stave_id) }}</div>
                    <div><strong>Schedule:</strong> {{ builderConfig.schedule || 'Manual' }}</div>
                    <div><strong>Status:</strong> {{ builderConfig.is_active ? 'Active' : 'Inactive' }}</div>
                  </div>
                </div>
                
                <div>
                  <h5 class="font-medium text-gray-900 dark:text-white mb-2">Thresholds</h5>
                  <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    <div><strong>Warning:</strong> {{ builderConfig.warn || 'Not set' }}</div>
                    <div><strong>Failure:</strong> {{ builderConfig.fail || 'Not set' }}</div>
                  </div>
                </div>
              </div>
              
              <!-- Configuration -->
              <div>
                <h5 class="font-medium text-gray-900 dark:text-white mb-2">Configuration</h5>
                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <pre class="text-sm text-gray-700 dark:text-gray-300">{{ JSON.stringify(builderConfig.configuration, null, 2) }}</pre>
                </div>
              </div>
              
              <!-- Description -->
              <div v-if="builderConfig.description">
                <h5 class="font-medium text-gray-900 dark:text-white mb-2">Description</h5>
                <p class="text-sm text-gray-600 dark:text-gray-400">{{ builderConfig.description }}</p>
              </div>
            </div>
          </UCard>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex items-center justify-between pt-6">
        <UButton 
          v-if="currentStep > 0"
          color="gray" 
          variant="outline"
          icon="i-heroicons-chevron-left"
          @click="previousStep"
        >
          Previous
        </UButton>
        <div v-else></div>
        
        <div class="flex items-center space-x-3">
          <UButton 
            v-if="currentStep < steps.length - 1"
            color="primary"
            icon="i-heroicons-chevron-right"
            icon-right
            @click="nextStep"
            :disabled="!canProceed"
          >
            Next
          </UButton>
          <UButton 
            v-else
            color="green"
            icon="i-heroicons-check"
            @click="createClef"
            :loading="isCreating"
          >
            Create Clef
          </UButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { CreateClefRequest } from '~/services/clefs'

interface Props {
  clefTemplates: Array<{
    type: string
    name: string
    description: string
    icon: string
    tier: number
    config: Record<string, any>
  }>
  staveOptions: Array<{ label: string; value: string }>
  scheduleOptions: Array<{ label: string; value: string }>
}

interface Emits {
  (e: 'create', clef: CreateClefRequest): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// State
const currentStep = ref(0)
const selectedType = ref('')
const isCreating = ref(false)

const steps = ['Choose Type', 'Configure', 'Schedule', 'Review']

// Builder configuration
const builderConfig = ref<CreateClefRequest>({
  name: '',
  description: '',
  stave_id: '',
  check_type: '',
  configuration: {},
  schedule: '',
  is_active: true,
  warn: '',
  fail: ''
})

// Computed
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return selectedType.value !== ''
    case 1:
      return builderConfig.value.name && builderConfig.value.stave_id
    case 2:
      return true // Schedule and thresholds are optional
    case 3:
      return true
    default:
      return false
  }
})

// Methods
const getStepClass = (index: number) => {
  if (index < currentStep.value) {
    return 'bg-green-500 text-white'
  } else if (index === currentStep.value) {
    return 'bg-blue-500 text-white'
  } else {
    return 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
  }
}

const getStepTextClass = (index: number) => {
  if (index <= currentStep.value) {
    return 'text-gray-900 dark:text-white'
  } else {
    return 'text-gray-500 dark:text-gray-400'
  }
}

const getTierColor = (tier: number): string => {
  const colors = { 1: 'blue', 2: 'green', 3: 'yellow', 4: 'purple' }
  return colors[tier as keyof typeof colors] || 'gray'
}

const getTierDescription = (tier: number): string => {
  const descriptions = {
    1: 'Basic',
    2: 'Advanced', 
    3: 'Cross-System',
    4: 'Custom'
  }
  return descriptions[tier as keyof typeof descriptions] || 'Unknown'
}

const selectType = (type: string) => {
  selectedType.value = type
  builderConfig.value.check_type = type
  
  const template = props.clefTemplates.find(t => t.type === type)
  if (template) {
    builderConfig.value.configuration = { ...template.config }
  }
}

const getSelectedTemplate = () => {
  return props.clefTemplates.find(t => t.type === selectedType.value)
}

const getTips = () => {
  const template = getSelectedTemplate()
  if (!template) return []
  
  const tips: Record<string, string[]> = {
    'row_count': [
      'Set realistic min/max values based on your data volume',
      'Consider seasonal variations in your data',
      'Use percentage thresholds for better flexibility'
    ],
    'freshness': [
      'Choose a timestamp column that represents data updates',
      'Set appropriate max_age_hours based on your SLA',
      'Consider different freshness requirements for different data types'
    ],
    'column_values': [
      'Start with null checks for critical fields',
      'Use regex patterns for format validation',
      'Set reasonable thresholds to avoid false positives'
    ],
    'forecast': [
      'Ensure you have sufficient historical data',
      'Choose the right aggregation level for your use case',
      'Monitor model performance over time'
    ],
    'data_profile_drift': [
      'Use stable reference periods for comparison',
      'Consider business context when interpreting drift',
      'Start with key business metrics'
    ],
    'lookup_validation': [
      'Ensure lookup sources are reliable and up-to-date',
      'Use appropriate join strategies',
      'Consider data latency between systems'
    ],
    'python': [
      'Keep scripts focused and well-documented',
      'Use proper error handling',
      'Test scripts thoroughly before deployment'
    ]
  }
  
  return tips[template.type] || []
}

const getScheduleDescription = (schedule: string) => {
  const descriptions: Record<string, string> = {
    '': 'Manual execution only',
    '0 * * * *': 'Every hour',
    '0 */6 * * *': 'Every 6 hours',
    '0 0 * * *': 'Daily at midnight',
    '0 0 * * 0': 'Weekly on Sunday',
    '0 0 1 * *': 'Monthly on the 1st'
  }
  return descriptions[schedule] || 'Custom schedule'
}

const getStaveName = (staveId: string) => {
  const stave = props.staveOptions.find(s => s.value === staveId)
  return stave?.label || 'Unknown Stave'
}

const nextStep = () => {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

const previousStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const createClef = async () => {
  isCreating.value = true
  try {
    emit('create', { ...builderConfig.value })
  } finally {
    isCreating.value = false
  }
}
</script>













