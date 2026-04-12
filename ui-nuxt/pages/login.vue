<template>
  <div class="min-h-screen dm-app overflow-hidden flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative">
    <!-- Aesthetic Additions -->
    <div class="bg-noise"></div>
    <div class="ambient-glow" style="top: -20vh; left: -20vw; width: 80vw; height: 80vh; opacity: 0.6;"></div>
    <div class="ambient-glow-2" style="bottom: -20vh; right: -20vw; width: 80vw; height: 80vh; opacity: 0.4;"></div>

    <div class="max-w-md w-full space-y-8 z-10">
      <!-- Logo and Header -->
      <div class="text-center">
        <div
          class="flex items-center justify-center w-20 h-20 shadow-lg shadow-cyan-500/20 mx-auto mb-4 rounded-lg gradient-primary"
        >
          <Icon name="lucide:music" class="w-10 h-10 text-white" />
        </div>
        <h2 class="text-5xl animate-stagger-1 font-bold text-white tracking-tight">DataMetronome</h2>
        <p class="mt-2 text-lg text-slate-400 animate-stagger-2 mb-8">
          Sign in to your data quality monitoring platform
        </p>
      </div>

      <!-- Login Form -->
      <UCard class="glass-card animate-stagger-3 !border-slate-800/60 !bg-slate-900/40 !backdrop-blur-xl shadow-2xl">
        <UForm :state="form" :schema="schema" class="space-y-6" @submit="handleLogin">
          <UFormGroup label="Username" name="username">
            <UInput
              v-model="form.username"
              placeholder="Enter your username"
              icon="i-heroicons-user"
              autocomplete="username"
            />
          </UFormGroup>

          <UFormGroup label="Password" name="password">
            <UInput
              v-model="form.password"
              type="password"
              placeholder="Enter your password"
              icon="i-heroicons-lock-closed"
              autocomplete="current-password"
            />
          </UFormGroup>

          <div class="flex items-center justify-between">
            <UCheckbox v-model="form.rememberMe" label="Remember me" />
            <UButton color="gray" variant="link" size="md" @click="showForgotPassword = true">
              Forgot password?
            </UButton>
          </div>

          <UAlert
            v-if="errorMessage"
            color="red"
            variant="soft"
            :title="errorMessage"
            icon="i-heroicons-exclamation-triangle"
          />

          <UButton type="submit" color="primary" size="xl" class="text-lg py-3 font-semibold tracking-wide" block :loading="isLoading">
            Sign In
          </UButton>
        </UForm>
      </UCard>

    </div>

    <!-- Forgot Password Modal -->
    <UModal v-model="showForgotPassword">
      <UCard class="glass-card animate-stagger-3 !border-slate-800/60 !bg-slate-900/40 !backdrop-blur-xl shadow-2xl">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-2xl font-bold text-white">Reset Password</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showForgotPassword = false"
            />
          </div>
        </template>
        <p class="text-slate-300 text-base">
          Password reset functionality will be implemented in a future version. Please contact your
          administrator.
        </p>
        <template #footer>
          <div class="flex justify-end">
            <UButton color="primary" @click="showForgotPassword = false"> OK </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { z } from 'zod'

const authStore = useAuthStore()

const isLoading = ref(false)
const showForgotPassword = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: '',
  rememberMe: false,
})

const schema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

async function handleLogin() {
  isLoading.value = true
  errorMessage.value = ''

  // Chrome autofill doesn't always trigger Vue input events.
  // Read DOM values as fallback so autofilled credentials are captured.
  const usernameInput = document.querySelector<HTMLInputElement>('input[name="username"]')
  const passwordInput = document.querySelector<HTMLInputElement>('input[name="password"]')
  const username = form.username || usernameInput?.value || ''
  const password = form.password || passwordInput?.value || ''

  try {
    const result = await authStore.login({
      username,
      password,
    })

    if (result.success) {
      await navigateTo('/')
    } else {
      errorMessage.value = result.error || 'Incorrect username or password'
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Login failed'
  } finally {
    isLoading.value = false
  }
}

// Redirect if already authenticated
onMounted(() => {
  if (authStore.isAuthenticated) {
    navigateTo('/')
  }
})

// Set page meta
useHead({
  title: 'Login - DataMetronome',
})
</script>
