<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <!-- Logo and Header -->
      <div class="text-center">
        <div class="flex items-center justify-center w-16 h-16 mx-auto mb-4 rounded-lg gradient-primary">
          <Icon name="lucide:music" class="w-8 h-8 text-white" />
        </div>
        <h2 class="text-3xl font-bold text-gray-900 dark:text-white">
          DataMetronome
        </h2>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Sign in to your data quality monitoring platform
        </p>
      </div>

      <!-- Login Form -->
      <UCard>
        <UForm
          :state="form"
          :schema="schema"
          @submit="handleLogin"
          class="space-y-6"
        >
          <UFormGroup label="Username" name="username">
            <UInput
              v-model="form.username"
              placeholder="Enter your username"
              icon="i-heroicons-user"
            />
          </UFormGroup>

          <UFormGroup label="Password" name="password">
            <UInput
              v-model="form.password"
              type="password"
              placeholder="Enter your password"
              icon="i-heroicons-lock-closed"
            />
          </UFormGroup>

          <div class="flex items-center justify-between">
            <UCheckbox
              v-model="form.rememberMe"
              label="Remember me"
            />
            <UButton
              color="gray"
              variant="link"
              size="sm"
              @click="showForgotPassword = true"
            >
              Forgot password?
            </UButton>
          </div>

          <UButton
            type="submit"
            color="primary"
            size="lg"
            block
            :loading="isLoading"
          >
            Sign In
          </UButton>
        </UForm>
      </UCard>

      <!-- Demo Credentials -->
      <UCard>
        <template #header>
          <h3 class="text-sm font-medium text-gray-900 dark:text-white">
            Demo Credentials
          </h3>
        </template>
        <div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p><strong>Username:</strong> admin</p>
          <p><strong>Password:</strong> admin</p>
        </div>
      </UCard>
    </div>

    <!-- Forgot Password Modal -->
    <UModal v-model="showForgotPassword">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Reset Password</h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="showForgotPassword = false"
            />
          </div>
        </template>
        <p class="text-gray-600 dark:text-gray-400">
          Password reset functionality will be implemented in a future version.
          For now, please use the demo credentials above.
        </p>
        <template #footer>
          <div class="flex justify-end">
            <UButton
              color="primary"
              @click="showForgotPassword = false"
            >
              OK
            </UButton>
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

const form = reactive({
  username: 'admin',
  password: 'admin',
  rememberMe: false
})

const schema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required')
})

async function handleLogin() {
  isLoading.value = true
  
  try {
    const result = await authStore.login({
      username: form.username,
      password: form.password
    })
    
    if (result.success) {
      // Show success message
      console.log('Login successful!')
      // Navigate to dashboard
      await navigateTo('/')
    } else {
      // Show error message
      console.error('Login failed:', result.error)
      // You could add a toast notification here
    }
  } catch (error) {
    console.error('Login error:', error)
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
  title: 'Login - DataMetronome'
})
</script>
