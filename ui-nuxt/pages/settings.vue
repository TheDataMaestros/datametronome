<template>
  <div class="space-y-6">
    <div>
      <p class="dm-label mb-2">Administration</p>
      <h1
        style="font-family: var(--dm-font-display); font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
      >
        Settings
      </h1>
    </div>

    <!-- Admin gate -->
    <div v-if="!isAdmin" class="intelligence-panel rounded-xl p-6 text-center">
      <Icon name="i-heroicons-lock-closed" class="w-8 h-8 text-slate-500 mx-auto mb-3" />
      <p class="text-slate-400 text-sm">Only administrators can manage settings.</p>
    </div>

    <template v-else>
      <!-- AI Provider Configuration -->
      <div class="intelligence-panel rounded-xl p-5">
        <div class="flex items-center gap-2 mb-5">
          <Icon name="i-heroicons-cpu-chip" class="w-4 h-4 text-blue-400" />
          <p class="text-sm font-semibold text-white">AI Provider Configuration</p>
          <span v-if="isDirty" class="text-[10px] text-amber-400 ml-auto">Unsaved changes</span>
        </div>

        <div v-if="loading" class="text-center py-8 text-slate-500 text-sm">Loading settings...</div>

        <div v-else class="space-y-4">
          <!-- Provider -->
          <div>
            <label class="block text-xs text-slate-400 mb-1.5">Provider</label>
            <select
              v-model="form.ai_provider"
              class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
            >
              <option value="ollama">Ollama (local)</option>
              <option value="anthropic">Anthropic</option>
              <option value="openai">OpenAI</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>

          <!-- Model -->
          <div>
            <label class="block text-xs text-slate-400 mb-1.5">Model</label>
            <input
              v-model="form.ai_model"
              type="text"
              placeholder="e.g. claude-sonnet-4-6, gpt-4o, qwen2.5"
              class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          <!-- API Key -->
          <div>
            <label class="block text-xs text-slate-400 mb-1.5">API Key</label>
            <div class="relative">
              <input
                v-model="form.ai_api_key"
                :type="showKey ? 'text' : 'password'"
                placeholder="sk-..."
                class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 pr-10 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
              />
              <button
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                @click="showKey = !showKey"
              >
                <Icon :name="showKey ? 'i-heroicons-eye-slash' : 'i-heroicons-eye'" class="w-4 h-4" />
              </button>
            </div>
            <p class="text-[10px] text-slate-600 mt-1">Not required for Ollama. Encrypted at rest.</p>
          </div>

          <!-- Base URL -->
          <div>
            <label class="block text-xs text-slate-400 mb-1.5">Base URL <span class="text-slate-600">(optional)</span></label>
            <input
              v-model="form.ai_base_url"
              type="text"
              placeholder="e.g. http://localhost:11434/v1"
              class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          <!-- Router Model -->
          <div>
            <label class="block text-xs text-slate-400 mb-1.5">Router Model <span class="text-slate-600">(optional, cheaper model for intent routing)</span></label>
            <input
              v-model="form.ai_router_model"
              type="text"
              placeholder="Falls back to main model if empty"
              class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          <!-- Heavy Model -->
          <div>
            <label class="block text-xs text-slate-400 mb-1.5">Heavy Model <span class="text-slate-600">(optional, for complex analysis)</span></label>
            <input
              v-model="form.ai_heavy_model"
              type="text"
              placeholder="Falls back to main model if empty"
              class="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-2">
            <button
              :disabled="saving || !isDirty"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="isDirty
                ? 'bg-blue-600 hover:bg-blue-500 text-white'
                : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'"
              @click="save"
            >
              {{ saving ? 'Saving...' : 'Save Changes' }}
            </button>
            <button
              v-if="isDirty"
              class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white border border-slate-700/50 hover:border-slate-600 transition-colors"
              @click="resetForm"
            >
              Discard
            </button>
            <p v-if="saveMessage" class="text-xs ml-auto" :class="saveError ? 'text-red-400' : 'text-emerald-400'">
              {{ saveMessage }}
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { settingsService, type AppSetting } from '~/services/settings'

definePageMeta({ middleware: 'auth', layout: 'dashboard' })
useHead({ title: 'Settings - DataMetronome' })

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')

const MASKED = '\u25cf\u25cf\u25cf\u25cf\u25cf\u25cf'

const loading = ref(true)
const saving = ref(false)
const showKey = ref(false)
const saveMessage = ref('')
const saveError = ref(false)

interface SettingsForm {
  ai_provider: string
  ai_model: string
  ai_api_key: string
  ai_base_url: string
  ai_router_model: string
  ai_heavy_model: string
}

const defaults: SettingsForm = {
  ai_provider: 'ollama',
  ai_model: 'qwen2.5',
  ai_api_key: '',
  ai_base_url: '',
  ai_router_model: '',
  ai_heavy_model: '',
}

const form = reactive<SettingsForm>({ ...defaults })
const saved = ref<SettingsForm>({ ...defaults })

const isDirty = computed(() => {
  return (Object.keys(defaults) as (keyof SettingsForm)[]).some(k => form[k] !== saved.value[k])
})

function resetForm() {
  Object.assign(form, saved.value)
  saveMessage.value = ''
}

async function loadSettings() {
  loading.value = true
  try {
    const all = await settingsService.getAll()
    const map = Object.fromEntries(all.map(s => [s.key, s.value]))
    for (const key of Object.keys(defaults) as (keyof SettingsForm)[]) {
      if (map[key] !== undefined) {
        form[key] = map[key]
      }
    }
    saved.value = { ...form }
  } catch {
    // No settings yet — use defaults
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  saveMessage.value = ''
  saveError.value = false
  try {
    for (const key of Object.keys(defaults) as (keyof SettingsForm)[]) {
      if (form[key] !== saved.value[key]) {
        // Skip if user didn't change masked API key
        if (form[key] === MASKED) continue
        // Only save non-empty values; delete empty ones to fall back to env
        if (form[key]) {
          await settingsService.set(key, form[key])
        } else {
          try { await settingsService.remove(key) } catch { /* not found is fine */ }
        }
      }
    }
    // Reload to get server state
    await loadSettings()
    saveMessage.value = 'Settings saved'
    setTimeout(() => { saveMessage.value = '' }, 3000)
  } catch (err: any) {
    saveError.value = true
    saveMessage.value = err?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (isAdmin.value) loadSettings()
  else loading.value = false
})
</script>
