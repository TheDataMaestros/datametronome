import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'
import { config, buildApiUrl } from '~/config/app'

/**
 * Session tokens live in localStorage for SPA simplicity. XSS on this origin can
 * read them; production deployments should prefer httpOnly cookies or document the risk.
 */

export interface User {
  username: string
  email: string
  name: string
  role?: 'admin' | 'editor' | 'viewer'
  is_active?: boolean
}

async function fetchCurrentUser(accessToken: string): Promise<User | null> {
  const response = await fetch(buildApiUrl('/auth/me'), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: 'application/json',
    },
  })
  if (!response.ok) {
    return null
  }
  const me = await response.json()
  const username = String(me.username ?? '')
  return {
    username,
    email: String(me.email ?? ''),
    name: username || String(me.email ?? ''),
    role: (me.role as 'admin' | 'editor' | 'viewer') ?? 'viewer',
    is_active: Boolean(me.is_active),
  }
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

  // Treat presence of a token as authenticated.
  // (On refresh, user info may not be available yet / may fail to parse, but we still
  // want to keep the session and let the app fetch/derive user details later.)
  const isAuthenticated = computed(() => !!token.value)

  // Whether this page load has confirmed the stored token is still good.
  const sessionChecked = ref(false)

  async function login(credentials: LoginCredentials): Promise<LoginResult> {
    isLoading.value = true
    error.value = null

    try {
      // Call the real backend API
      const response = await fetch(buildApiUrl('/auth/login'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      })

      if (!response.ok) {
        const errorData = await response.json()
        const errorMsg = errorData.detail || 'Login failed'
        error.value = errorMsg
        return { success: false, error: errorMsg }
      }

      const data = await response.json()
      const authToken = data.access_token

      const profile = await fetchCurrentUser(authToken)
      const userData: User = profile ?? {
        username: credentials.username,
        email: '',
        name: credentials.username,
      }

      token.value = authToken
      user.value = userData

      // Store token in localStorage
      if (process.client) {
        localStorage.setItem('auth_token', authToken)
        localStorage.setItem('user_info', JSON.stringify(userData))
      }

      return { success: true, user: userData, token: authToken }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Login failed'
      error.value = errorMsg
      return { success: false, error: errorMsg }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * End the session.
   *
   * Pass redirect: false when the caller is already routing somewhere, such as
   * the auth middleware. Two navigations to /login mount the page twice, and
   * the first mount consumes the "why were you signed out" message before the
   * second one can show it.
   */
  async function logout({ redirect = true }: { redirect?: boolean } = {}): Promise<void> {
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
      if (redirect) await navigateTo('/login')
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
      const profile = await fetchCurrentUser(token.value)
      if (profile) {
        user.value = profile
        if (process.client) {
          localStorage.setItem('user_info', JSON.stringify(profile))
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to refresh user data'
      console.error('Error refreshing user data:', err)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Confirm the stored token still works, once per page load.
   *
   * A token in localStorage only means we had a session at some point. It can
   * be expired, signed with a rotated key, or belong to an account an admin
   * disabled. Without this check the app renders the whole logged-in shell on
   * a dead token, shows placeholder identity, loads nothing, and explains
   * none of it. Returns true when the session is usable.
   */
  async function ensureSessionValid(): Promise<boolean> {
    if (!token.value) return false
    if (sessionChecked.value) return true

    const profile = await fetchCurrentUser(token.value)
    sessionChecked.value = true

    if (!profile) {
      // The middleware does the redirect, so don't navigate here too.
      await logout({ redirect: false })
      // Set after logout, which clears error. The store survives the
      // client-side route change to /login, so the login page can read it
      // straight off the store with no sessionStorage round trip.
      error.value = 'Your session has ended. Please sign in again.'
      return false
    }

    user.value = profile
    if (process.client) {
      localStorage.setItem('user_info', JSON.stringify(profile))
    }
    return true
  }

  function initializeAuth(): void {
    if (process.client) {
      const storedToken = localStorage.getItem('auth_token')
      const storedUser = localStorage.getItem('user_info')

      if (storedToken) token.value = storedToken

      if (storedUser) {
        try {
          user.value = JSON.parse(storedUser)
        } catch (err) {
          console.error('Error parsing stored user data:', err)
          // Clear invalid user data, but keep the token so the session survives.
          localStorage.removeItem('user_info')
          user.value = null
        }
      }
    }
  }

  // Initialize auth state from localStorage on store creation
  initializeAuth()

  return {
    // State - don't use readonly for Pinia stores
    user,
    token,
    isLoading,
    error,

    // Computed
    isAuthenticated,

    // Actions
    login,
    logout,
    refreshUserData,
    initializeAuth,
    ensureSessionValid,
    sessionChecked,
  }
})
