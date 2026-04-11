<template>
  <div
    class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8"
  >
    <div class="max-w-md w-full space-y-8">
      <!-- Logo and Header -->
      <div class="text-center">
        <div
          class="flex items-center justify-center w-16 h-16 mx-auto mb-4 rounded-lg gradient-primary"
        >
          <Icon name="lucide:music" class="w-8 h-8 text-white" />
        </div>
        <h2 class="text-3xl font-bold text-gray-900 dark:text-white">DataMetronome</h2>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Welcome — let's set up your admin account
        </p>
      </div>

      <!-- Setup Form -->
      <UCard>
        <UForm :state="form" :schema="schema" class="space-y-6" @submit="handleSetup">
          <UFormGroup label="Username" name="username">
            <UInput
              v-model="form.username"
              placeholder="Choose a username"
              icon="i-heroicons-user"
            />
          </UFormGroup>

          <UFormGroup label="Email" name="email">
            <UInput
              v-model="form.email"
              type="email"
              placeholder="admin@example.com"
              icon="i-heroicons-envelope"
            />
          </UFormGroup>

          <UFormGroup label="Password" name="password">
            <UInput
              v-model="form.password"
              type="password"
              placeholder="At least 8 characters"
              icon="i-heroicons-lock-closed"
            />
          </UFormGroup>

          <UFormGroup label="Confirm Password" name="confirmPassword">
            <UInput
              v-model="form.confirmPassword"
              type="password"
              placeholder="Re-enter your password"
              icon="i-heroicons-lock-closed"
            />
          </UFormGroup>

          <UAlert
            v-if="errorMessage"
            color="red"
            variant="soft"
            :title="errorMessage"
            icon="i-heroicons-exclamation-triangle"
          />

          <UButton type="submit" color="primary" size="lg" block :loading="isLoading">
            Create Admin Account
          </UButton>
        </UForm>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { z } from 'zod'
import { buildApiUrl } from '~/config/app'

definePageMeta({ layout: false })

const authStore = useAuthStore()

const isLoading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const schema = z
  .object({
    username: z.string().min(3, 'Username must be at least 3 characters'),
    email: z.string().email('Invalid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

async function handleSetup() {
  errorMessage.value = ''
  isLoading.value = true

  try {
    const response = await fetch(buildApiUrl('/auth/setup/init'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.username,
        email: form.email,
        password: form.password,
      }),
    })

    if (response.status === 409) {
      // Setup already done
      await navigateTo('/login')
      return
    }

    if (!response.ok) {
      const data = await response.json()
      errorMessage.value = data.detail || 'Setup failed'
      return
    }

    const data = await response.json()
    const token = data.access_token

    // Store token and fetch user profile (reuse auth store login flow)
    if (process.client) {
      localStorage.setItem('auth_token', token)
    }
    authStore.token = token

    // Fetch user info
    const meResponse = await fetch(buildApiUrl('/auth/me'), {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
    })
    if (meResponse.ok) {
      const me = await meResponse.json()
      const user = {
        username: me.username,
        email: me.email,
        name: me.username,
        role: me.role ?? 'admin',
        is_active: me.is_active,
      }
      authStore.user = user
      if (process.client) {
        localStorage.setItem('user_info', JSON.stringify(user))
      }
    }

    // Clear cached setup status
    if (process.client) {
      sessionStorage.removeItem('setup_status')
    }

    await navigateTo('/')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Setup failed'
  } finally {
    isLoading.value = false
  }
}

// Guard: if setup is already done, redirect to login
onMounted(async () => {
  try {
    const response = await fetch(buildApiUrl('/auth/setup/status'))
    if (response.ok) {
      const data = await response.json()
      if (!data.needs_setup) {
        await navigateTo('/login')
      }
    }
  } catch {
    // API not reachable — stay on setup page
  }
})

useHead({ title: 'Setup - DataMetronome' })
</script>
