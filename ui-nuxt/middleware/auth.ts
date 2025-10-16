export default defineNuxtRouteMiddleware((to, from) => {
  const authStore = useAuthStore()
  
  // If not authenticated and trying to access protected route
  if (!authStore.isAuthenticated && to.path !== '/login') {
    return navigateTo('/login')
  }
  
  // If authenticated and trying to access login page, redirect to dashboard
  if (authStore.isAuthenticated && to.path === '/login') {
    return navigateTo('/')
  }
})
