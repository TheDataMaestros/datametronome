<!-- ui-nuxt/components/DatasourceSelector.vue -->
<template>
  <div class="flex items-center gap-2 flex-wrap">
    <span class="text-[10px] text-slate-500 mr-1">View:</span>

    <!-- All pill -->
    <button
      class="ds-pill"
      :class="modelValue === null ? 'ds-pill--active' : 'ds-pill--default'"
      @click="$emit('update:modelValue', null)"
    >
      All
    </button>

    <!-- Pinned / visible source pills -->
    <button
      v-for="stave in visibleStaves"
      :key="stave.id"
      class="ds-pill ds-pill--source group relative"
      :class="modelValue === stave.id ? 'ds-pill--active' : 'ds-pill--default'"
      @click="$emit('update:modelValue', stave.id)"
    >
      <!-- Health dot -->
      <span class="ds-dot" :style="{ background: healthColor(stave.id) }" />
      {{ stave.name }}
      <!-- Star — ghost shown via CSS .group:hover rule; filled shown when pinned or favourites active -->
      <span
        class="ds-star"
        :class="isPinned(stave.id) ? 'ds-star--filled' : (atMax && !isPinned(stave.id)) ? 'ds-star--disabled' : 'ds-star--ghost'"
        :title="isPinned(stave.id) ? 'Unpin' : atMax && !isPinned(stave.id) ? 'Max 3 pinned' : 'Pin to bar'"
        @click.stop="togglePin(stave.id)"
      >{{ isPinned(stave.id) ? '★' : '☆' }}</span>
    </button>

    <!-- Others dropdown -->
    <div v-if="othersStaves.length" class="relative" ref="othersRef">
      <button
        class="ds-pill ds-pill--others"
        @click="othersOpen = !othersOpen"
      >
        Others ({{ othersStaves.length }}) ▾
      </button>
      <div v-if="othersOpen" class="ds-dropdown">
        <button
          v-for="stave in othersStaves"
          :key="stave.id"
          class="ds-dropdown-item"
          @click="selectStave(stave.id)"
        >
          <span class="ds-dot" :style="{ background: healthColor(stave.id) }" />
          <span class="flex-1 text-left truncate max-w-[140px]">{{ stave.name }}</span>
          <span class="text-xs font-mono" :style="{ color: healthColor(stave.id) }">
            {{ staveHealthScores[stave.id] ?? '–' }}
          </span>
          <span
            class="ds-star ml-1"
            :class="isPinned(stave.id) ? 'ds-star--filled' : atMax ? 'ds-star--disabled' : 'ds-star--ghost'"
            :title="atMax && !isPinned(stave.id) ? 'Max 3 pinned' : isPinned(stave.id) ? 'Unpin' : 'Pin to bar'"
            @click.stop="togglePin(stave.id)"
          >{{ isPinned(stave.id) ? '★' : '☆' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onClickOutside } from '@vueuse/core'
import { healthColor as getHealthColor } from '~/utils/healthColor'

interface Stave { id: string; name: string }

const props = defineProps<{
  modelValue: string | null
  staves: Stave[]
  staveHealthScores: Record<string, number>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const { pinnedStaveIds, hasFavourites, atMax, isPatching, pinStave, unpinStave } = useDashboardPrefs()

const othersOpen = ref(false)
const othersRef = ref<HTMLElement | null>(null)

onClickOutside(othersRef, () => { othersOpen.value = false })

// Pills to show inline: pinned (if any favourites set) or first 3 worst-health
const visibleStaves = computed<Stave[]>(() => {
  if (hasFavourites.value) {
    return pinnedStaveIds.value
      .map((id) => props.staves.find((s) => s.id === id))
      .filter(Boolean) as Stave[]
  }
  // No favourites: show worst 3 (scored first, then unscored alphabetically)
  const scored = props.staves
    .filter((s) => props.staveHealthScores[s.id] !== undefined)
    .sort((a, b) => (props.staveHealthScores[a.id] ?? 999) - (props.staveHealthScores[b.id] ?? 999))
  const unscored = props.staves
    .filter((s) => props.staveHealthScores[s.id] === undefined)
    .sort((a, b) => a.name.localeCompare(b.name))
  return [...scored, ...unscored].slice(0, 3)
})

const othersStaves = computed<Stave[]>(() => {
  const visibleIds = new Set(visibleStaves.value.map((s) => s.id))
  return props.staves.filter((s) => !visibleIds.has(s.id))
})

function isPinned(id: string) { return pinnedStaveIds.value.includes(id) }

async function togglePin(id: string) {
  if (isPatching.value) return
  if (isPinned(id)) {
    await unpinStave(id)
  } else if (!atMax.value) {
    await pinStave(id)
  }
}

function selectStave(id: string) {
  emit('update:modelValue', id)
  othersOpen.value = false
}

function healthColor(id: string): string {
  return getHealthColor(props.staveHealthScores[id])
}
</script>

<style scoped>
.ds-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.ds-pill--active { background: #1d4ed8; color: white; border-color: #3b82f6; }
.ds-pill--default { background: #1e293b; color: #e2e8f0; border-color: #334155; }
.ds-pill--default:hover { border-color: #475569; }
.ds-pill--others { background: #1e293b; color: #64748b; border-color: #334155; }
.ds-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.ds-star { font-size: 11px; cursor: pointer; transition: color 0.1s; }
.ds-star--filled { color: #f59e0b; }
.ds-star--ghost { color: #475569; opacity: 0; }
.ds-star--ghost:hover, .group:hover .ds-star--ghost { opacity: 1; color: #f59e0b; }
.ds-star--disabled { color: #334155; cursor: not-allowed; }

.ds-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 50;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 6px;
  min-width: 220px;
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ds-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
  width: 100%;
  text-align: left;
}
.ds-dropdown-item:hover { background: #263347; color: #e2e8f0; }
</style>
