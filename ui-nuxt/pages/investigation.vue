<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
          Investigation
        </h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Investigate and explore your data with custom queries and analysis tools.
        </p>
      </div>
    </div>

    <!-- Coming Soon -->
    <UCard>
      <div class="text-center py-12">
        <Icon name="i-heroicons-magnifying-glass" class="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Data Investigation Tools
        </h3>
        <p class="text-gray-600 dark:text-gray-400 mb-6">
          This feature is coming soon! It will include custom SQL queries, 
          data profiling, sample data viewing, and interactive data exploration.
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
  title: 'Investigation - DataMetronome'
})
</script>
