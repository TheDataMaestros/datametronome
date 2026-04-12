<template>
  <div class="dm-shell">
    <!-- Aesthetic Additions -->
    <div class="bg-noise"></div>
    <div class="ambient-glow"></div>
    <div class="ambient-glow-2"></div>

    <!-- ===================== SIDEBAR ===================== -->
    <aside class="dm-sidebar" :class="{ 'is-collapsed': collapsed }">
      <!-- Logo -->
      <div class="dm-sidebar__logo">
        <div class="dm-logo-icon">
          <div class="dm-logo-icon__bg" />
          <div class="dm-logo-icon__pulse" />
          <svg class="dm-logo-icon__svg" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 2.5L18.5 17.5H1.5L10 2.5Z" stroke="rgba(255,255,255,0.9)" stroke-width="1.35" stroke-linejoin="round" />
            <line x1="10" y1="16" x2="14.8" y2="7.2" stroke="white" stroke-width="1.35" stroke-linecap="round" />
            <circle cx="14.8" cy="6.6" r="1.4" fill="white" />
            <circle cx="10" cy="16" r="0.8" fill="rgba(255,255,255,0.55)" />
          </svg>
        </div>
        <div class="dm-logo-text">
          <span class="dm-logo-text__brand">DataMetronome</span>
          <span class="dm-logo-text__sub">Data Quality Platform</span>
        </div>
        <!-- Collapse toggle -->
        <button class="dm-collapse-btn" :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'" @click="toggleCollapse">
          <Icon
            :name="collapsed ? 'i-heroicons-chevron-right' : 'i-heroicons-chevron-left'"
            class="w-3.5 h-3.5"
          />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="dm-nav">
        <span class="dm-nav__section-label">Navigation</span>
        <NuxtLink
          v-for="item in navigationItems"
          :key="item.to"
          :to="item.to"
          class="dm-nav__item"
          :class="{ 'is-active': isActive(item.to) }"
          :title="collapsed ? item.label : undefined"
        >
          <span class="dm-nav__accent" />
          <Icon :name="item.icon" class="dm-nav__icon" />
          <span class="dm-nav__label">{{ item.label }}</span>
          <UBadge
            v-if="item.badge && !collapsed"
            :color="item.badgeColor"
            variant="solid"
            size="xs"
            class="ml-auto text-xs"
          >
            {{ item.badge }}
          </UBadge>
        </NuxtLink>

        <!-- Admin section -->
        <template v-if="isAdmin">
          <span class="dm-nav__section-label" style="margin-top: 12px">Admin</span>
          <NuxtLink
            v-for="item in adminItems"
            :key="item.to"
            :to="item.to"
            class="dm-nav__item"
            :class="{ 'is-active': isActive(item.to) }"
            :title="collapsed ? item.label : undefined"
          >
            <span class="dm-nav__accent" />
            <Icon :name="item.icon" class="dm-nav__icon" />
            <span class="dm-nav__label">{{ item.label }}</span>
          </NuxtLink>
        </template>
      </nav>

      <!-- Stave Selector -->
      <div class="dm-stave-section" v-if="!collapsed">
        <span class="dm-nav__section-label">Datasource</span>
        <div class="dm-stave-picker" ref="stavePicker">
          <button class="dm-stave-trigger" @click="staveOpen = !staveOpen">
            <template v-if="selectedStaveId">
              <span
                class="dm-stave-dot"
                :style="{ background: selectedStaveHealthColor }"
              />
              <span class="dm-stave-name">{{ selectedSlaveName }}</span>
            </template>
            <template v-else>
              <Icon name="i-heroicons-circle-stack" class="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
              <span class="dm-stave-placeholder">Select Stave</span>
            </template>
            <Icon name="i-heroicons-chevron-up-down" class="w-3.5 h-3.5 text-slate-500 ml-auto flex-shrink-0" />
          </button>
          <div v-if="staveOpen" class="dm-stave-dropdown">
            <button
              class="dm-stave-option"
              :class="{ 'is-active': selectedStaveId === null }"
              @click="pickStave(null)"
            >
              <span class="dm-stave-dot" style="background: #475569" />
              <span>All sources</span>
            </button>
            <button
              v-for="stave in sidebarStaves"
              :key="stave.id"
              class="dm-stave-option"
              :class="{ 'is-active': selectedStaveId === stave.id }"
              @click="pickStave(stave.id)"
            >
              <span class="dm-stave-dot" :style="{ background: staveColor(stave.id) }" />
              <span class="truncate">{{ stave.name }}</span>
              <span class="ml-auto text-[10px] font-mono" :style="{ color: staveColor(stave.id) }">
                {{ sidebarHealthScores[stave.id] ?? '' }}
              </span>
            </button>
          </div>
        </div>
      </div>
      <!-- Collapsed stave dot indicator -->
      <div v-else-if="selectedStaveId" class="flex justify-center py-2">
        <span
          class="w-2 h-2 rounded-full"
          :style="{ background: selectedStaveHealthColor }"
          :title="selectedSlaveName"
        />
      </div>

      <!-- User Footer -->
      <div class="dm-sidebar__footer">
        <div class="dm-user" :title="collapsed ? (user?.name || 'Admin User') : undefined">
          <UAvatar :src="user?.avatar || undefined" :alt="user?.name || 'Admin'" size="sm" />
          <div class="dm-user__info">
            <span class="dm-user__name">{{ user?.name || 'Admin User' }}</span>
            <span class="dm-user__email">{{ user?.email || 'admin@datametronome.dev' }}</span>
          </div>
          <UDropdown :items="userMenuItems">
            <button class="dm-user__menu-btn">
              <Icon name="i-heroicons-ellipsis-vertical" class="w-3.5 h-3.5" />
            </button>
          </UDropdown>
        </div>
      </div>
    </aside>

    <!-- ===================== MAIN ===================== -->
    <div class="dm-main" :style="{ marginLeft: collapsed ? '62px' : '256px' }">
      <!-- Header -->
      <header class="dm-header">
        <div class="dm-header__left">
          <h2 class="dm-page-title">{{ pageTitle }}</h2>
        </div>

        <div class="dm-header__right">
          <!-- Notification bell + dropdown -->
          <div ref="notifRef" class="dm-notif-wrapper">
            <button
              class="dm-header__action"
              :class="{ 'dm-header__action--active': showNotifications }"
              title="Notifications"
              @click="toggleNotifications"
            >
              <Icon name="i-heroicons-bell" class="w-4 h-4" />
              <span v-if="unreadCount > 0" class="dm-notif-dot">
                {{ unreadCount > 9 ? '9+' : unreadCount }}
              </span>
            </button>

            <Transition name="dm-notif-panel">
              <div v-if="showNotifications" class="dm-notif-panel">
                <div class="dm-notif-panel__header">
                  <span class="dm-notif-panel__title">Notifications</span>
                  <button v-if="unreadCount > 0" class="dm-notif-panel__mark-all" @click="markAllRead">
                    Mark all read
                  </button>
                </div>
                <div v-if="isLoading" class="dm-notif-panel__empty">
                  <Icon name="i-heroicons-arrow-path" class="w-5 h-5 animate-spin opacity-40" />
                </div>
                <div v-else-if="notifications.length === 0" class="dm-notif-panel__empty">
                  <Icon name="i-heroicons-bell-slash" class="w-8 h-8 mb-2 opacity-20" />
                  <p class="dm-notif-panel__empty-title">No new notifications</p>
                  <p class="dm-notif-panel__empty-sub">Failed and warning checks will appear here</p>
                </div>
                <div v-else class="dm-notif-panel__list">
                  <button
                    v-for="n in notifications.slice(0, 5)"
                    :key="n.id"
                    class="dm-notif-item"
                    :class="{ 'dm-notif-item--unread': !n.read }"
                    @click="handleNotifClick(n)"
                  >
                    <span class="dm-notif-item__icon" :class="`dm-notif-item__icon--${n.type}`">
                      <Icon :name="n.type === 'error' ? 'i-heroicons-x-circle' : 'i-heroicons-exclamation-triangle'" class="w-3.5 h-3.5" />
                    </span>
                    <span class="dm-notif-item__content">
                      <span class="dm-notif-item__title">{{ n.title }}</span>
                      <span class="dm-notif-item__body">{{ n.body }}</span>
                      <span class="dm-notif-item__meta">{{ n.source }} · {{ formatTimeAgo(n.timestamp) }}</span>
                    </span>
                    <span v-if="!n.read" class="dm-notif-item__unread-dot" />
                  </button>
                </div>
                <div class="dm-notif-panel__footer">
                  <NuxtLink to="/notifications" class="dm-notif-panel__see-all" @click="showNotifications = false">
                    See all notifications
                    <Icon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
                  </NuxtLink>
                </div>
              </div>
            </Transition>
          </div>

          <button class="dm-header__action" title="Settings" @click="showSettings = !showSettings">
            <Icon name="i-heroicons-cog-6-tooth" class="w-4 h-4" />
          </button>

          <button class="dm-header__btn-primary" :disabled="isRefreshing" @click="refreshData">
            <Icon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" :class="{ 'animate-spin': isRefreshing }" />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      <!-- Page Content -->
      <main class="dm-content">
        <slot />
      </main>
    </div>

    <ChatWidget />
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'
import { useNotifications } from '~/composables/useNotifications'
import { healthColor } from '~/utils/healthColor'

const authStore = useAuthStore()
const route = useRoute()

const { notifications, unreadCount, isLoading, fetchNotifications, markRead, markAllRead } =
  useNotifications()

// ── Collapse state (persisted) ──────────────────────────────────────────────
const COLLAPSE_KEY = 'dm:sidebar-collapsed'

const collapsed = ref(false)

onMounted(() => {
  try {
    collapsed.value = localStorage.getItem(COLLAPSE_KEY) === 'true'
  } catch {}
  fetchNotifications()
})

function toggleCollapse() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem(COLLAPSE_KEY, String(collapsed.value))
  } catch {}
}

// ── Page title ───────────────────────────────────────────────────────────────
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    index: 'Dashboard',
    anomalies: 'Anomalies',
    'ml-anomalies': 'ML Anomalies',
    trends: 'Trends & Patterns',
    staves: 'Data Sources',
    clefs: 'Quality Checks',
    chat: 'Chat History',
    reports: 'Reports',
    investigation: 'Investigation',
    insights: 'AI Insights',
    notifications: 'Notifications',
    profile: 'Profile',
    settings: 'Settings',
    users: 'Users',
  }
  return titles[route.name as string] || 'DataMetronome'
})

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

// ── Auth / user ──────────────────────────────────────────────────────────────
const user = computed(() => authStore.user)
const isAdmin = computed(() => authStore.user?.role === 'admin')
const showNotifications = ref(false)
const showSettings = ref(false)
const isRefreshing = ref(false)
const notifRef = ref<HTMLElement | null>(null)

onClickOutside(notifRef, () => { showNotifications.value = false })

function toggleNotifications() {
  showNotifications.value = !showNotifications.value
}

function handleNotifClick(n: { id: string; type: string }) {
  markRead(n.id)
  showNotifications.value = false
  navigateTo('/notifications')
}

function formatTimeAgo(timestamp: string) {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  const diffMin = Math.floor((Date.now() - date.getTime()) / 60_000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  return `${Math.floor(diffH / 24)}d ago`
}

// ── Navigation ───────────────────────────────────────────────────────────────
const navigationItems = [
  { to: '/', icon: 'i-heroicons-squares-2x2', label: 'Dashboard', badge: null },
  { to: '/anomalies', icon: 'i-heroicons-exclamation-triangle', label: 'Anomalies', badge: null, badgeColor: 'red' },
  { to: '/trends', icon: 'i-heroicons-chart-bar', label: 'Trends', badge: null },
  { to: '/insights', icon: 'i-heroicons-sparkles', label: 'AI Insights', badge: null },
  { to: '/staves', icon: 'i-heroicons-server', label: 'Data Sources', badge: null },
  { to: '/clefs', icon: 'i-heroicons-check-circle', label: 'Quality Checks', badge: null },
  { to: '/chat', icon: 'i-heroicons-chat-bubble-left-right', label: 'Chat', badge: null },
  { to: '/reports', icon: 'i-heroicons-document-chart-bar', label: 'Reports', badge: null },
  { to: '/investigation', icon: 'i-heroicons-magnifying-glass', label: 'Investigation', badge: null },
]

const adminItems = [
  { to: '/users', icon: 'i-heroicons-users', label: 'Users' },
  { to: '/settings', icon: 'i-heroicons-cog-6-tooth', label: 'Settings' },
]

const userMenuItems = [
  [{ label: 'Profile', icon: 'i-heroicons-user', click: () => navigateTo('/profile') }],
  [{ label: 'Settings', icon: 'i-heroicons-cog-6-tooth', click: () => navigateTo('/settings') }],
  [{ label: 'Sign out', icon: 'i-heroicons-arrow-right-on-rectangle', click: () => authStore.logout() }],
]

// ── Stave picker ─────────────────────────────────────────────────────────────
const { selectedStaveId, selectStave } = useSelectedStave()
const { staves, fetchStaves } = useStaves()
const { metrics: dashboardMetrics, fetchMetrics } = useDashboard()

const staveOpen = ref(false)
const stavePicker = ref<HTMLElement | null>(null)
onClickOutside(stavePicker, () => { staveOpen.value = false })

const sidebarStaves = computed(() => staves.value ?? [])
const sidebarHealthScores = computed<Record<string, number>>(
  () => (dashboardMetrics.value as any)?.intelligence?.stave_health_scores ?? {}
)

function staveColor(id: string) { return healthColor(sidebarHealthScores.value[id]) }

const selectedSlaveName = computed(() => {
  if (!selectedStaveId.value) return null
  return sidebarStaves.value.find((s: any) => s.id === selectedStaveId.value)?.name ?? selectedStaveId.value
})

const selectedStaveHealthColor = computed(() =>
  healthColor(selectedStaveId.value ? sidebarHealthScores.value[selectedStaveId.value] : undefined)
)

function pickStave(id: string | null) {
  selectStave(id)
  staveOpen.value = false
  if (route.path !== '/') navigateTo('/')
}

onMounted(() => {
  fetchStaves()
  fetchMetrics()
})

async function refreshData() {
  isRefreshing.value = true
  try {
    await Promise.all([authStore.refreshUserData(), fetchNotifications()])
    await new Promise((resolve) => setTimeout(resolve, 600))
  } finally {
    isRefreshing.value = false
  }
}
</script>

<style scoped>
.dm-stave-section {
  padding: 0 10px 8px;
}
.dm-stave-picker {
  position: relative;
}
.dm-stave-trigger {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 7px 10px;
  border-radius: 8px;
  background: #0f1117;
  border: 1px solid #1e293b;
  color: #94a3b8;
  font-size: 15.6px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.dm-stave-trigger:hover { border-color: #334155; }
.dm-stave-name { flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #e2e8f0; font-weight: 500; }
.dm-stave-placeholder { flex: 1; text-align: left; color: #475569; font-style: italic; }
.dm-stave-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
.dm-stave-dropdown {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 0; right: 0;
  z-index: 100;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 4px;
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.dm-stave-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 15.6px;
  color: #94a3b8;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: background 0.1s;
}
.dm-stave-option:hover { background: #263347; color: #e2e8f0; }
.dm-stave-option.is-active { background: #1e3a5f; color: white; }
</style>
