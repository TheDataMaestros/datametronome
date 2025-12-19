export default defineNuxtRouteMiddleware((to) => {
  const authStore = useAuthStore()

  // On a hard refresh, Nuxt route middleware runs during SSR.
  // Our auth state is rehydrated from localStorage (client-only), so on the server
  // `isAuthenticated` will be false and we'd incorrectly redirect to /login.
  // Defer auth decisions to the client.
  if (import.meta.server) return

  // If the store was first created during SSR, it won't have run the client-side
  // localStorage rehydration. Ensure it's initialized before checking auth.
  authStore.initializeAuth()

  // If not authenticated and trying to access protected route
  if (!authStore.isAuthenticated && to.path !== '/login') {
    return navigateTo('/login')
  }

  // If authenticated and trying to access login page, redirect to dashboard
  if (authStore.isAuthenticated && to.path === '/login') {
    return navigateTo('/')
  }
})
