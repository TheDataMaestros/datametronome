import { defineStore } from 'pinia'

export interface User {
  username: string
  email: string
  name: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface LoginResult {
  success: boolean
  error?: string
  user?: User
  token?: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  async function login(credentials: LoginCredentials): Promise<LoginResult> {
    isLoading.value = true
    error.value = null

    try {
      // Simulate API call - in real app this would call your Podium API
      await new Promise(resolve => setTimeout(resolve, 500))

      // Simple demo authentication
      if (credentials.username === 'admin' && credentials.password === 'admin') {
        const authToken = 'demo-token-' + Date.now()
        const userData: User = {
          username: credentials.username,
          email: 'admin@datametronome.dev',
          name: 'Admin User'
        }

        token.value = authToken
        user.value = userData

        // Store token in localStorage
        if (process.client) {
          localStorage.setItem('auth_token', authToken)
          localStorage.setItem('user_info', JSON.stringify(userData))
        }

        return { success: true, user: userData, token: authToken }
      } else {
        const errorMsg = 'Invalid credentials'
        error.value = errorMsg
        return { success: false, error: errorMsg }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Login failed'
      error.value = errorMsg
      return { success: false, error: errorMsg }
    } finally {
      isLoading.value = false
    }
  }

  async function logout(): Promise<void> {
    isLoading.value = true
    
    try {
      // Clear state
      token.value = null
      user.value = null
      error.value = null

      // Clear localStorage
      if (process.client) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_info')
      }

      // Navigate to login
      await navigateTo('/login')
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function refreshUserData(): Promise<void> {
    if (!token.value) return

    isLoading.value = true
    error.value = null

    try {
      // Simulate API call to refresh user data
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // In a real app, you would call your API here
      // const response = await apiService.get('/auth/me')
      // user.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to refresh user data'
      console.error('Error refreshing user data:', err)
    } finally {
      isLoading.value = false
    }
  }

  function initializeAuth(): void {
    if (process.client) {
      const storedToken = localStorage.getItem('auth_token')
      const storedUser = localStorage.getItem('user_info')
      
      if (storedToken && storedUser) {
        try {
          token.value = storedToken
          user.value = JSON.parse(storedUser)
        } catch (err) {
          console.error('Error parsing stored user data:', err)
          // Clear invalid data
          localStorage.removeItem('auth_token')
          localStorage.removeItem('user_info')
        }
      }
    }
  }

  // Initialize auth state from localStorage on store creation
  initializeAuth()

  return {
    // State
    user: readonly(user),
    token: readonly(token),
    isLoading: readonly(isLoading),
    error: readonly(error),
    
    // Computed
    isAuthenticated,
    
    // Actions
    login,
    logout,
    refreshUserData,
    initializeAuth,
  }
})
