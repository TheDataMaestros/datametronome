<template>
  <div class="space-y-6">
    <div>
      <p class="dm-label mb-2">Account</p>
      <h1
        style="font-family: var(--dm-font-display); font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
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

    <!-- Password -->
    <div class="intelligence-panel rounded-xl p-5">
      <div class="flex items-center gap-2 mb-5">
        <Icon name="i-heroicons-key" class="w-4 h-4 text-blue-400" />
        <p class="text-sm font-semibold text-white">Change Password</p>
      </div>

      <form class="space-y-4 max-w-md" @submit.prevent="submitPasswordChange">
        <div>
          <label class="block text-xs text-slate-400 mb-1.5">Current password</label>
          <input
            v-model="passwordForm.current"
            type="password"
            autocomplete="current-password"
            class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          />
        </div>

        <div>
          <label class="block text-xs text-slate-400 mb-1.5">New password</label>
          <input
            v-model="passwordForm.next"
            type="password"
            autocomplete="new-password"
            class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          />
          <p class="text-[10px] text-slate-600 mt-1">At least 8 characters.</p>
        </div>

        <div>
          <label class="block text-xs text-slate-400 mb-1.5">Confirm new password</label>
          <input
            v-model="passwordForm.confirm"
            type="password"
            autocomplete="new-password"
            class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          />
        </div>

        <UAlert
          v-if="passwordMessage"
          :color="passwordFailed ? 'red' : 'green'"
          variant="soft"
          :icon="passwordFailed ? 'i-heroicons-exclamation-triangle' : 'i-heroicons-check-circle'"
          :title="passwordMessage"
        />

        <UButton type="submit" color="primary" :loading="isChangingPassword">
          Update password
        </UButton>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { buildApiUrl } from '~/config/app'
import { healthColor as getHealthColor } from '~/utils/healthColor'
import type { Stave } from '~/services/staves'

definePageMeta({ middleware: 'auth', layout: 'dashboard' })
useHead({ title: 'Profile - DataMetronome' })

const { staves, fetchStaves } = useStaves()
const { pinnedStaveIds, atMax, isPatching, loadPrefs, pinStave, unpinStave, reorderPinned } =
  useDashboardPrefs()
const { metrics: dashboardMetrics, fetchMetrics } = useDashboard()

// ── Change own password ──────────────────────────────────────────────────────
const authStore = useAuthStore()
const passwordForm = reactive({ current: '', next: '', confirm: '' })
const isChangingPassword = ref(false)
const passwordMessage = ref('')
const passwordFailed = ref(false)

async function submitPasswordChange() {
  passwordMessage.value = ''
  passwordFailed.value = false

  // Confirmation is checked here only. The server never sees it, and cannot
  // tell a typo from an intended password.
  if (passwordForm.next !== passwordForm.confirm) {
    passwordFailed.value = true
    passwordMessage.value = 'The two new passwords do not match.'
    return
  }

  isChangingPassword.value = true
  try {
    const response = await fetch(buildApiUrl('/auth/me/password'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({
        current_password: passwordForm.current,
        new_password: passwordForm.next,
      }),
    })

    const data = await response.json().catch(() => null)
    if (!response.ok) {
      passwordFailed.value = true
      const detail = data?.detail
      passwordMessage.value = Array.isArray(detail)
        ? detail.map((d: any) => d.msg).join('. ')
        : detail || 'Could not update the password.'
      return
    }

    passwordMessage.value = 'Password updated.'
    passwordForm.current = ''
    passwordForm.next = ''
    passwordForm.confirm = ''
  } catch {
    passwordFailed.value = true
    passwordMessage.value = 'Could not reach the server.'
  } finally {
    isChangingPassword.value = false
  }
}

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
