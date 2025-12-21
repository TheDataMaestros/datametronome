<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Sidebar -->
    <div class="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 shadow-lg">
      <!-- Header -->
      <div class="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-center w-8 h-8 rounded-lg gradient-primary">
          <Icon name="i-heroicons-musical-note" class="w-5 h-5 text-white" />
        </div>
        <div class="flex flex-col">
          <h1 class="text-lg font-bold text-gray-900 dark:text-white">DataMetronome</h1>
          <p class="text-xs text-gray-500 dark:text-gray-400">Data Quality Platform</p>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-3 py-4 space-y-1">
        <NuxtLink
          v-for="item in navigationItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors"
          :class="[
            $route.path === item.to
              ? 'bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-300'
              : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700',
          ]"
        >
          <Icon :name="item.icon" class="w-5 h-5" />
          <span>{{ item.label }}</span>
          <UBadge v-if="item.badge" :color="item.badgeColor" size="sm" class="ml-auto">
            {{ item.badge }}
          </UBadge>
        </NuxtLink>
      </nav>

      <!-- Footer -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-700">
        <div class="flex items-center gap-3">
          <UAvatar :src="user?.avatar || undefined" :alt="user?.name || 'Admin User'" size="sm" />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
              {{ user?.name || 'Admin User' }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400 truncate">
              {{ user?.email || 'admin@datametronome.dev' }}
            </p>
          </div>
          <UDropdown :items="userMenuItems">
            <UButton color="gray" variant="ghost" icon="i-heroicons-ellipsis-vertical" size="sm" />
          </UDropdown>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="pl-64">
      <!-- Top Navigation -->
      <header
        class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700"
      >
        <div class="px-6 py-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
                {{ pageTitle }}
              </h2>
            </div>
            <div class="flex items-center gap-3">
              <UButton
                color="gray"
                variant="ghost"
                icon="i-heroicons-bell"
                :badge="notificationCount > 0 ? notificationCount : undefined"
                @click="showNotifications = !showNotifications"
              />
              <UButton
                color="gray"
                variant="ghost"
                icon="i-heroicons-cog-6-tooth"
                @click="showSettings = !showSettings"
              />
              <UButton
                color="primary"
                variant="solid"
                icon="i-heroicons-arrow-path"
                @click="refreshData"
                :loading="isRefreshing"
              >
                Refresh
              </UButton>
            </div>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'

const authStore = useAuthStore()

const route = useRoute()
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    index: 'Dashboard',
    anomalies: 'Anomalies',
    trends: 'Trends & Patterns',
    staves: 'Data Sources',
    clefs: 'Quality Checks',
    settings: 'Settings',
  }
  return titles[route.name as string] || 'DataMetronome'
})

const user = computed(() => authStore.user)
const notificationCount = ref(3)
const showNotifications = ref(false)
const showSettings = ref(false)
const isRefreshing = ref(false)

const navigationItems = [
  {
    to: '/',
    icon: 'i-heroicons-home',
    label: 'Dashboard',
    badge: null,
  },
  {
    to: '/anomalies',
    icon: 'i-heroicons-exclamation-triangle',
    label: 'Anomalies',
    badge: '2',
    badgeColor: 'red',
  },
  {
    to: '/trends',
    icon: 'i-heroicons-chart-bar',
    label: 'Trends & Patterns',
    badge: null,
  },
  {
    to: '/staves',
    icon: 'i-heroicons-server',
    label: 'Data Sources',
    badge: null,
  },
  {
    to: '/clefs',
    icon: 'i-heroicons-check-circle',
    label: 'Quality Checks',
    badge: null,
  },
]

const userMenuItems = [
  [
    {
      label: 'Profile',
      icon: 'i-heroicons-user',
      click: () => navigateTo('/profile'),
    },
  ],
  [
    {
      label: 'Settings',
      icon: 'i-heroicons-cog-6-tooth',
      click: () => navigateTo('/settings'),
    },
  ],
  [
    {
      label: 'Sign out',
      icon: 'i-heroicons-arrow-right-on-rectangle',
      click: () => authStore.logout(),
    },
  ],
]

async function refreshData() {
  isRefreshing.value = true
  try {
    // Refresh all data stores
    await Promise.all([
      authStore.refreshUserData(),
      // Add other store refresh calls here
    ])
    await new Promise((resolve) => setTimeout(resolve, 1000)) // Simulate refresh
  } finally {
    isRefreshing.value = false
  }
}
</script>
