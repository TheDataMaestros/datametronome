<template>
  <div class="space-y-6">
    <div>
      <p class="dm-label mb-2">Check Result</p>
      <h1
        style="font-family: var(--dm-font-display); font-size: 2.4rem; font-weight: 800; letter-spacing: -0.05em; color: var(--dm-text-primary); line-height: 1.1;"
      >
        {{ clefName || 'Check' }}
      </h1>
      <p v-if="check" class="mt-2 text-sm" style="color: var(--dm-text-secondary);">
        {{ staveName || check.stave_id }} · {{ formatTime(check.timestamp) }}
      </p>
    </div>

    <div v-if="isLoading" class="dm-card p-6 text-sm" style="color: var(--dm-text-secondary);">
      Loading check…
    </div>

    <div v-else-if="error" class="dm-card p-6">
      <p class="text-sm font-medium" style="color: var(--dm-danger, #dc2626);">{{ error }}</p>
      <p class="mt-2 text-xs" style="color: var(--dm-text-secondary);">
        Alert links point here by check id. A missing check usually means it was
        pruned, or the link came from a different environment.
      </p>
      <UButton class="mt-4" color="gray" variant="ghost" to="/clefs">Back to checks</UButton>
    </div>

    <template v-else-if="check">
      <div class="dm-card p-6 space-y-4">
        <div class="flex items-center gap-3">
          <span class="text-2xl">{{ statusIcon }}</span>
          <div>
            <p class="text-lg font-semibold" style="color: var(--dm-text-primary);">
              {{ check.status }}
            </p>
            <p v-if="check.severity" class="text-xs" style="color: var(--dm-text-secondary);">
              {{ check.severity }}
            </p>
          </div>
        </div>

        <p v-if="check.message" class="text-sm" style="color: var(--dm-text-primary);">
          {{ check.message }}
        </p>

        <dl class="grid grid-cols-2 gap-4 pt-2 sm:grid-cols-4">
          <div v-for="f in facts" :key="f.label">
            <dt class="text-xs uppercase tracking-wide" style="color: var(--dm-text-secondary);">
              {{ f.label }}
            </dt>
            <dd class="mt-1 text-sm" style="color: var(--dm-text-primary);">{{ f.value }}</dd>
          </div>
        </dl>
      </div>

      <div v-if="detailEntries.length" class="dm-card p-6">
        <p class="dm-label mb-3">Evidence</p>
        <dl class="space-y-2">
          <div v-for="[key, value] in detailEntries" :key="key" class="flex gap-3 text-sm">
            <dt class="w-48 shrink-0" style="color: var(--dm-text-secondary);">{{ key }}</dt>
            <dd class="break-all" style="color: var(--dm-text-primary);">{{ format(value) }}</dd>
          </div>
        </dl>
      </div>

      <UButton color="gray" variant="ghost" to="/clefs">Back to checks</UButton>
    </template>
  </div>
</template>

<script setup lang="ts">
import { checksService, type Check } from '~/services/checks'
import { clefsService } from '~/services/clefs'
import { stavesService } from '~/services/staves'

definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({ title: 'Check Result - DataMetronome' })

const route = useRoute()
const check = ref<Check | null>(null)
// The checks API returns ids, not names, so the labels are fetched alongside.
const clefName = ref('')
const staveName = ref('')
const isLoading = ref(true)
const error = ref<string | null>(null)

const ICONS: Record<string, string> = { pass: '✅', warn: '⚠️', fail: '❌', error: '❌' }
const statusIcon = computed(() => ICONS[check.value?.status ?? ''] ?? '❓')

const facts = computed(() => {
  const c = check.value
  if (!c) return []
  const out = [{ label: 'Check type', value: c.check_type }]
  if (c.execution_time != null) out.push({ label: 'Duration', value: `${c.execution_time.toFixed(2)}s` })
  if (c.anomalies_count != null) out.push({ label: 'Anomalies', value: String(c.anomalies_count) })
  if (c.data_source_type) out.push({ label: 'Source', value: c.data_source_type })
  return out
})

// `details` is the API name; `metadata` is the older alias still sent by some paths.
const detailEntries = computed(() =>
  Object.entries(check.value?.details ?? check.value?.metadata ?? {}),
)

function format(value: unknown) {
  return typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)
}

function formatTime(timestamp: string) {
  const date = new Date(timestamp)
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString()
}

onMounted(async () => {
  try {
    const result = await checksService.getById(String(route.params.id))
    check.value = result
    // Names are cosmetic: a failure here must not blank the page.
    const [clef, stave] = await Promise.allSettled([
      clefsService.getById(result.clef_id),
      stavesService.getById(result.stave_id),
    ])
    if (clef.status === 'fulfilled') clefName.value = clef.value.name
    if (stave.status === 'fulfilled') staveName.value = stave.value.name
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Check not found'
  } finally {
    isLoading.value = false
  }
})
</script>
