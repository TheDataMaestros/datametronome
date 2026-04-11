import { buildApiUrl } from '~/config/app'

let setupStatusCache: { needs_setup: boolean; ts: number } | null = null
const CACHE_TTL_MS = 30_000 // 30 seconds

async function checkNeedsSetup(): Promise<boolean> {
  // Check sessionStorage first (survives navigations, cleared on tab close)
  if (process.client) {
    const stored = sessionStorage.getItem('setup_status')
    if (stored !== null) {
      return stored === 'true'
    }
  }

  // Check in-memory cache
  if (setupStatusCache && Date.now() - setupStatusCache.ts < CACHE_TTL_MS) {
    return setupStatusCache.needs_setup
  }

  try {
    const response = await fetch(buildApiUrl('/auth/setup/status'))
    if (response.ok) {
      const data = await response.json()
      setupStatusCache = { needs_setup: data.needs_setup, ts: Date.now() }
      if (process.client) {
        sessionStorage.setItem('setup_status', String(data.needs_setup))
      }
      return data.needs_setup
    }
  } catch {
    // API unreachable — fall through to normal auth flow
  }
  return false
}

export default defineNuxtRouteMiddleware(async (to) => {
  const authStore = useAuthStore()

  // Defer auth decisions to client (localStorage not available during SSR)
  if (import.meta.server) return

  // Initialize auth state from localStorage
  authStore.initializeAuth()

  const needsSetup = await checkNeedsSetup()

  // /setup page: redirect away if setup is already done
  if (to.path === '/setup') {
    if (!needsSetup) {
      return navigateTo('/login')
    }
    return // allow access to setup page
  }

  // /login page: redirect to setup if needed, otherwise allow if unauthenticated
  if (to.path === '/login') {
    if (needsSetup) {
      return navigateTo('/setup')
    }
    if (authStore.isAuthenticated) {
      return navigateTo('/')
    }
    return
  }

  // Protected routes: check auth, redirect to setup or login
  if (!authStore.isAuthenticated) {
    if (needsSetup) {
      return navigateTo('/setup')
    }
    return navigateTo('/login')
  }
})
