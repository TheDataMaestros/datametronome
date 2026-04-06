<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <p class="dm-label mb-2">System Events</p>
        <h1
          style="font-family: var(--dm-font-display); font-size: 2rem; font-weight: 800; letter-spacing: -0.05em; color: var(--dm-text-primary); line-height: 1.1;"
        >
          Notifications
        </h1>
        <p class="mt-2 text-sm" style="color: var(--dm-text-secondary);">
          Failed and warning check results from your data quality monitors.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <UButton
          v-if="unreadCount > 0"
          color="gray"
          variant="ghost"
          icon="i-heroicons-check"
          @click="markAllRead"
        >
          Mark all read
        </UButton>
        <UButton
          color="gray"
          variant="ghost"
          icon="i-heroicons-arrow-path"
          :loading="isLoading"
          @click="fetchNotifications(100)"
        >
          Refresh
        </UButton>
      </div>
    </div>

    <!-- Filter tabs -->
    <div class="dm-tabs">
      <button
        class="dm-tab"
        :class="{ 'is-active': activeFilter === 'all' }"
        @click="activeFilter = 'all'"
      >
        All
        <span class="dm-tab-count">{{ notifications.length }}</span>
      </button>
      <button
        class="dm-tab"
        :class="{ 'is-active': activeFilter === 'unread' }"
        @click="activeFilter = 'unread'"
      >
        Unread
        <span v-if="unreadCount > 0" class="dm-tab-count dm-tab-count--accent">
          {{ unreadCount }}
        </span>
      </button>
      <button
        class="dm-tab"
        :class="{ 'is-active': activeFilter === 'error' }"
        @click="activeFilter = 'error'"
      >
        Failures
        <span class="dm-tab-count">{{ errorCount }}</span>
      </button>
      <button
        class="dm-tab"
        :class="{ 'is-active': activeFilter === 'warning' }"
        @click="activeFilter = 'warning'"
      >
        Warnings
        <span class="dm-tab-count">{{ warningCount }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="dm-notif-page-empty">
      <Icon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin opacity-20 mb-3" />
      <p style="color: var(--dm-text-muted); font-size: 13px;">Loading notifications…</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="filtered.length === 0" class="dm-notif-page-empty">
      <div class="dm-notif-page-empty__icon">
        <Icon name="i-heroicons-bell-slash" class="w-8 h-8 opacity-40" />
      </div>
      <p class="dm-notif-page-empty__title">No notifications</p>
      <p class="dm-notif-page-empty__sub">
        {{
          activeFilter === 'unread'
            ? 'All caught up — no unread notifications.'
            : 'No failed or warning checks to show.'
        }}
      </p>
    </div>

    <!-- Notification list -->
    <div v-else class="dm-notif-page-list">
      <!-- Group by date -->
      <div v-for="group in grouped" :key="group.label" class="dm-notif-group">
        <div class="dm-notif-group__label">{{ group.label }}</div>
        <div class="dm-notif-page-card">
          <button
            v-for="n in group.items"
            :key="n.id"
            class="dm-notif-page-item"
            :class="{ 'dm-notif-page-item--unread': !n.read }"
            @click="handleClick(n)"
          >
            <!-- Type icon -->
            <span class="dm-notif-item__icon" :class="`dm-notif-item__icon--${n.type}`">
              <Icon
                :name="
                  n.type === 'error'
                    ? 'i-heroicons-x-circle'
                    : 'i-heroicons-exclamation-triangle'
                "
                class="w-4 h-4"
              />
            </span>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-0.5">
                <span class="dm-notif-page-item__title">{{ n.title }}</span>
                <UBadge
                  :color="n.type === 'error' ? 'red' : 'yellow'"
                  variant="subtle"
                  size="xs"
                >
                  {{ n.type === 'error' ? 'Failed' : 'Warning' }}
                </UBadge>
              </div>
              <p class="dm-notif-page-item__body">{{ n.body }}</p>
              <p class="dm-notif-page-item__meta">
                {{ n.source }} · {{ formatTime(n.timestamp) }}
              </p>
            </div>

            <!-- Unread indicator -->
            <span v-if="!n.read" class="dm-notif-item__unread-dot flex-shrink-0" />
            <Icon
              v-else
              name="i-heroicons-check"
              class="w-4 h-4 flex-shrink-0 opacity-20"
            />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '~/composables/useNotifications'

definePageMeta({
  middleware: 'auth',
  layout: 'dashboard',
})

useHead({ title: 'Notifications - DataMetronome' })

const { notifications, unreadCount, isLoading, fetchNotifications, markRead, markAllRead } =
  useNotifications()

const activeFilter = ref<'all' | 'unread' | 'error' | 'warning'>('all')

const errorCount = computed(() => notifications.value.filter((n) => n.type === 'error').length)
const warningCount = computed(() => notifications.value.filter((n) => n.type === 'warning').length)

const filtered = computed(() => {
  switch (activeFilter.value) {
    case 'unread':
      return notifications.value.filter((n) => !n.read)
    case 'error':
      return notifications.value.filter((n) => n.type === 'error')
    case 'warning':
      return notifications.value.filter((n) => n.type === 'warning')
    default:
      return notifications.value
  }
})

const grouped = computed(() => {
  const groups: Record<string, typeof filtered.value> = {}
  for (const n of filtered.value) {
    const label = groupLabel(n.timestamp)
    if (!groups[label]) groups[label] = []
    groups[label].push(n)
  }
  return Object.entries(groups).map(([label, items]) => ({ label, items }))
})

function groupLabel(timestamp: string) {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / 86_400_000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
}

function formatTime(timestamp: string) {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  const diffMin = Math.floor((Date.now() - date.getTime()) / 60_000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function handleClick(n: { id: string }) {
  markRead(n.id)
  navigateTo('/clefs')
}

onMounted(() => {
  fetchNotifications(100)
})
</script>
