<template>
  <div class="space-y-6">
    <div>
      <p class="dm-label mb-2">Account</p>
      <h1
        style="font-family: var(--dm-font-display); font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
      >
        Profile
      </h1>
    </div>

    <!-- Dashboard Preferences -->
    <div class="intelligence-panel rounded-xl p-5">
      <div class="flex items-center gap-2 mb-5">
        <Icon name="i-heroicons-squares-2x2" class="w-4 h-4 text-blue-400" />
        <p class="text-sm font-semibold text-white">Dashboard Preferences</p>
        <span class="text-xs text-slate-500 ml-auto">Up to 3 pinned · drag to reorder</span>
      </div>

      <div v-if="sourcesLoading" class="text-center py-8 text-slate-500 text-sm">Loading sources...</div>

      <template v-else>
        <!-- Pinned sources (draggable) -->
        <div v-if="pinnedList.length" class="mb-4">
          <p class="text-[10px] uppercase tracking-widest text-amber-400 font-semibold mb-2">Pinned</p>
          <VueDraggable
            v-model="pinnedList"
            :animation="150"
            handle=".drag-handle"
            class="space-y-2"
            @end="savePinnedOrder"
          >
            <div
              v-for="stave in pinnedList"
              :key="stave.id"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50"
            >
              <Icon name="i-heroicons-bars-2" class="drag-handle w-4 h-4 text-slate-600 cursor-grab flex-shrink-0" />
              <span
                :style="{
                  background: healthColor(stave.id),
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  flexShrink: 0,
                  display: 'inline-block',
                }"
              />
              <span class="text-sm text-white font-medium flex-1">{{ stave.name }}</span>
              <span class="text-[10px] text-slate-500 bg-slate-700/50 px-1.5 py-0.5 rounded-full">
                {{ stave.data_source_type }}
              </span>
              <button
                class="text-xs px-2 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25 transition-colors"
                :disabled="isPatching"
                @click="unpinStave(stave.id)"
              >
                &#9733; Pinned
              </button>
            </div>
          </VueDraggable>
        </div>

        <!-- Other sources -->
        <div>
          <p class="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-2">Other Sources</p>
          <div class="space-y-2">
            <div
              v-for="stave in unpinnedStaves"
              :key="stave.id"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-800/30 border border-slate-700/30 opacity-70"
            >
              <span class="w-4 flex-shrink-0" />
              <span
                :style="{
                  background: healthColor(stave.id),
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  flexShrink: 0,
                  display: 'inline-block',
                }"
              />
              <span class="text-sm text-slate-400 flex-1">{{ stave.name }}</span>
              <span class="text-[10px] text-slate-600 bg-slate-700/30 px-1.5 py-0.5 rounded-full">
                {{ stave.data_source_type }}
              </span>
              <button
                class="text-xs px-2 py-1 rounded-lg border text-slate-500 transition-colors"
                :class="atMax ? 'border-slate-700/30 cursor-not-allowed' : 'border-slate-600/50 hover:border-amber-500/40 hover:text-amber-400'"
                :disabled="atMax || isPatching"
                :title="atMax ? 'Max 3 pinned' : 'Pin to dashboard bar'"
                @click="atMax ? undefined : pinStave(stave.id)"
              >
                &#9734; Pin{{ atMax ? ' (max reached)' : '' }}
              </button>
            </div>
            <p v-if="unpinnedStaves.length === 0" class="text-xs text-slate-600 py-2">All sources are pinned.</p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import { healthColor as getHealthColor } from '~/utils/healthColor'
import type { Stave } from '~/services/staves'

definePageMeta({ middleware: 'auth', layout: 'dashboard' })
useHead({ title: 'Profile - DataMetronome' })

const { staves, fetchStaves } = useStaves()
const { pinnedStaveIds, atMax, isPatching, loadPrefs, pinStave, unpinStave, reorderPinned } =
  useDashboardPrefs()
const { metrics: dashboardMetrics, fetchMetrics } = useDashboard()

const sourcesLoading = ref(true)

const staveHealthScores = computed<Record<string, number>>(
  () => dashboardMetrics.value?.intelligence?.stave_health_scores ?? {},
)

const pinnedStaves = computed<Stave[]>(() =>
  pinnedStaveIds.value
    .map((id) => staves.value.find((s) => s.id === id))
    .filter(Boolean) as Stave[],
)

const unpinnedStaves = computed<Stave[]>(() =>
  staves.value.filter((s) => !pinnedStaveIds.value.includes(s.id)),
)

// Mutable list for drag-to-reorder (mirrors pinnedStaves)
const pinnedList = ref<Stave[]>([])
watch(pinnedStaves, (val) => {
  pinnedList.value = [...val]
}, { immediate: true })

async function savePinnedOrder() {
  await reorderPinned(pinnedList.value.map((s) => s.id))
}

function healthColor(id: string): string {
  return getHealthColor(staveHealthScores.value[id])
}

onMounted(async () => {
  await Promise.all([fetchStaves(), loadPrefs(), fetchMetrics()])
  sourcesLoading.value = false
})
</script>
