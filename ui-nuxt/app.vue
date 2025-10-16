<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup lang="ts">
// Initialize auth state
const authStore = useAuthStore()
authStore.initializeAuth()
</script>
