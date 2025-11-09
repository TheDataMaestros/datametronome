<template>
  <div class="space-y-4">
    <!-- Row Count Configuration -->
    <div v-if="clefType === 'row_count'" class="space-y-4">
      <UFormGroup label="Table Name" required>
        <UInput 
          v-model="localConfig.table" 
          placeholder="e.g., users"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UFormGroup label="Minimum Expected Rows">
          <UInput 
            v-model.number="localConfig.expected_min" 
            type="number"
            placeholder="0"
            @input="updateConfig"
          />
        </UFormGroup>
        
        <UFormGroup label="Maximum Expected Rows">
          <UInput 
            v-model.number="localConfig.expected_max" 
            type="number"
            placeholder="1000000"
            @input="updateConfig"
          />
        </UFormGroup>
      </div>
    </div>

    <!-- Freshness Configuration -->
    <div v-else-if="clefType === 'freshness'" class="space-y-4">
      <UFormGroup label="Table Name" required>
        <UInput 
          v-model="localConfig.table" 
          placeholder="e.g., users"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Timestamp Column" required>
        <UInput 
          v-model="localConfig.column" 
          placeholder="e.g., updated_at"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Maximum Age (Hours)">
        <UInput 
          v-model.number="localConfig.max_age_hours" 
          type="number"
          placeholder="24"
          @input="updateConfig"
        />
      </UFormGroup>
    </div>

    <!-- Column Values Configuration -->
    <div v-else-if="clefType === 'column_values'" class="space-y-4">
      <UFormGroup label="Table Name" required>
        <UInput 
          v-model="localConfig.table" 
          placeholder="e.g., users"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Column Name" required>
        <UInput 
          v-model="localConfig.column" 
          placeholder="e.g., email"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Validation Type">
        <USelect
          v-model="localConfig.validation_type"
          :options="validationTypeOptions"
          @change="updateConfig"
        />
      </UFormGroup>
      
      <!-- Additional fields based on validation type -->
      <div v-if="localConfig.validation_type === 'null_check'" class="space-y-4">
        <UFormGroup label="Maximum NULL Percentage">
          <UInput 
            v-model.number="localConfig.threshold" 
            type="number"
            step="0.01"
            placeholder="0.01"
            @input="updateConfig"
          />
        </UFormGroup>
      </div>
      
      <div v-else-if="localConfig.validation_type === 'range_check'" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UFormGroup label="Minimum Value">
            <UInput 
              v-model.number="localConfig.min" 
              type="number"
              placeholder="0"
              @input="updateConfig"
            />
          </UFormGroup>
          
          <UFormGroup label="Maximum Value">
            <UInput 
              v-model.number="localConfig.max" 
              type="number"
              placeholder="100"
              @input="updateConfig"
            />
          </UFormGroup>
        </div>
      </div>
      
      <div v-else-if="localConfig.validation_type === 'pattern_check'" class="space-y-4">
        <UFormGroup label="Regex Pattern">
          <UInput 
            v-model="localConfig.pattern" 
            placeholder="^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"
            @input="updateConfig"
          />
        </UFormGroup>
      </div>
    </div>

    <!-- Forecast Configuration -->
    <div v-else-if="clefType === 'forecast'" class="space-y-4">
      <UFormGroup label="Table Name" required>
        <UInput 
          v-model="localConfig.table" 
          placeholder="e.g., events"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Metric to Monitor">
        <USelect
          v-model="localConfig.metric"
          :options="metricOptions"
          @change="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Time Column" required>
        <UInput 
          v-model="localConfig.time_column" 
          placeholder="e.g., created_at"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UFormGroup label="Aggregation">
          <USelect
            v-model="localConfig.aggregation"
            :options="aggregationOptions"
            @change="updateConfig"
          />
        </UFormGroup>
        
        <UFormGroup label="Model">
          <USelect
            v-model="localConfig.model"
            :options="modelOptions"
            @change="updateConfig"
          />
        </UFormGroup>
      </div>
    </div>

    <!-- Data Profile Drift Configuration -->
    <div v-else-if="clefType === 'data_profile_drift'" class="space-y-4">
      <UFormGroup label="Table Name" required>
        <UInput 
          v-model="localConfig.table" 
          placeholder="e.g., users"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Column Name" required>
        <UInput 
          v-model="localConfig.column" 
          placeholder="e.g., age"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UFormGroup label="Reference Period">
          <USelect
            v-model="localConfig.reference_period"
            :options="periodOptions"
            @change="updateConfig"
          />
        </UFormGroup>
        
        <UFormGroup label="Comparison Period">
          <USelect
            v-model="localConfig.comparison_period"
            :options="periodOptions"
            @change="updateConfig"
          />
        </UFormGroup>
      </div>
    </div>

    <!-- Lookup Validation Configuration -->
    <div v-else-if="clefType === 'lookup_validation'" class="space-y-4">
      <UFormGroup label="Source Table" required>
        <UInput 
          v-model="localConfig.source_table" 
          placeholder="e.g., users"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Source Column" required>
        <UInput 
          v-model="localConfig.source_column" 
          placeholder="e.g., id"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Lookup Source">
        <UInput 
          v-model="localConfig.lookup_source" 
          placeholder="e.g., analytics_db"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Lookup Query">
        <UTextarea 
          v-model="localConfig.lookup_query" 
          placeholder="SELECT DISTINCT user_id FROM user_events"
          rows="3"
          @input="updateConfig"
        />
      </UFormGroup>
    </div>

    <!-- Python Configuration -->
    <div v-else-if="clefType === 'python'" class="space-y-4">
      <UFormGroup label="Script Path" required>
        <UInput 
          v-model="localConfig.script_path" 
          placeholder="e.g., scripts/user_validation.py"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Function Name" required>
        <UInput 
          v-model="localConfig.function_name" 
          placeholder="e.g., check_user_compliance"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Parameters (JSON)">
        <UTextarea 
          v-model="parametersJson" 
          placeholder='{"min_age": 18, "required_fields": ["email", "name"]}'
          rows="4"
          @input="updateParameters"
        />
      </UFormGroup>
    </div>

    <!-- Default Configuration -->
    <div v-else class="space-y-4">
      <UFormGroup label="Table Name">
        <UInput 
          v-model="localConfig.table" 
          placeholder="e.g., users"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Column Name">
        <UInput 
          v-model="localConfig.column" 
          placeholder="e.g., email"
          @input="updateConfig"
        />
      </UFormGroup>
      
      <UFormGroup label="Custom Configuration (JSON)">
        <UTextarea 
          v-model="customConfigJson" 
          placeholder='{"key": "value"}'
          rows="4"
          @input="updateCustomConfig"
        />
      </UFormGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface Props {
  clefType: string
  config: Record<string, any>
}

interface Emits {
  (e: 'update:config', config: Record<string, any>): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Local config state
const localConfig = ref<Record<string, any>>({ ...props.config })

// JSON string representations for complex fields
const parametersJson = ref('')
const customConfigJson = ref('')

// Options for various selects
const validationTypeOptions = [
  { label: 'NULL Check', value: 'null_check' },
  { label: 'Range Check', value: 'range_check' },
  { label: 'Pattern Check', value: 'pattern_check' },
  { label: 'Uniqueness Check', value: 'uniqueness_check' }
]

const metricOptions = [
  { label: 'Row Count', value: 'row_count' },
  { label: 'Sum', value: 'sum' },
  { label: 'Average', value: 'avg' },
  { label: 'Count Distinct', value: 'count_distinct' }
]

const aggregationOptions = [
  { label: 'Hourly', value: 'hourly' },
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly', value: 'monthly' }
]

const modelOptions = [
  { label: 'SARIMA', value: 'sarima' },
  { label: 'Prophet', value: 'prophet' },
  { label: 'LSTM', value: 'lstm' }
]

const periodOptions = [
  { label: 'Last 7 Days', value: 'last_7_days' },
  { label: 'Last 30 Days', value: 'last_30_days' },
  { label: 'Last 90 Days', value: 'last_90_days' }
]

// Methods
const updateConfig = () => {
  emit('update:config', { ...localConfig.value })
}

const updateParameters = () => {
  try {
    const parsed = JSON.parse(parametersJson.value || '{}')
    localConfig.value.parameters = parsed
    updateConfig()
  } catch (error) {
    console.warn('Invalid JSON in parameters:', error)
  }
}

const updateCustomConfig = () => {
  try {
    const parsed = JSON.parse(customConfigJson.value || '{}')
    Object.assign(localConfig.value, parsed)
    updateConfig()
  } catch (error) {
    console.warn('Invalid JSON in custom config:', error)
  }
}

// Watch for prop changes
watch(() => props.config, (newConfig) => {
  localConfig.value = { ...newConfig }
  
  // Update JSON representations
  if (newConfig.parameters) {
    parametersJson.value = JSON.stringify(newConfig.parameters, null, 2)
  }
  
  if (Object.keys(newConfig).length > 0) {
    customConfigJson.value = JSON.stringify(newConfig, null, 2)
  }
}, { deep: true })

// Initialize JSON representations
if (props.config.parameters) {
  parametersJson.value = JSON.stringify(props.config.parameters, null, 2)
}
</script>















