<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
          Quality Checks
        </h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Configure and manage your data quality checks and monitoring rules.
        </p>
      </div>
    </div>

    <!-- Coming Soon -->
    <UCard>
      <div class="text-center py-12">
        <Icon name="i-heroicons-check-circle" class="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Quality Check Management
        </h3>
        <p class="text-gray-600 dark:text-gray-400 mb-6">
          This feature is coming soon! It will include data quality rule configuration, 
          check scheduling, result monitoring, and performance tracking.
        </p>
        <UButton color="primary" @click="navigateTo('/')">
          Back to Dashboard
        </UButton>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
// Use middleware for authentication
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})
useHead({
  title: 'Quality Checks - DataMetronome'
})
</script>
