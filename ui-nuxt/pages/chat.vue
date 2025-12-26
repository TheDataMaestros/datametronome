<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Chat History</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          View and manage your conversation history with the AI assistant
        </p>
      </div>
      <div class="flex items-center gap-2">
        <UButton
          color="gray"
          variant="ghost"
          icon="i-heroicons-arrow-path"
          :loading="isLoading"
          @click="loadConversations"
        >
          Refresh
        </UButton>
        <UButton color="primary" icon="i-heroicons-plus" @click="startNewConversation">
          New Conversation
        </UButton>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && conversations.length === 0" class="text-center py-12">
      <Icon name="i-heroicons-arrow-path" class="w-8 h-8 text-gray-400 dark:text-gray-500 mx-auto mb-4 animate-spin" />
      <p class="text-gray-500 dark:text-gray-400">Loading conversations...</p>
    </div>

    <!-- Conversations List -->
    <div v-if="conversations.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <UCard
        v-for="conversation in conversations"
        :key="conversation.id"
        class="cursor-pointer hover:shadow-lg transition-shadow"
        @click="loadConversation(conversation.id)"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-semibold text-gray-900 dark:text-white truncate">
              {{ conversation.title }}
            </h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-trash"
              size="xs"
              @click.stop="deleteConversation(conversation.id)"
            />
          </div>
        </template>

        <div class="text-sm text-gray-500 dark:text-gray-400">
          <div class="flex items-center gap-2">
            <Icon name="i-heroicons-clock" class="w-4 h-4" />
            <span>{{ formatDate(conversation.updatedAt) }}</span>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Empty State -->
    <div v-else-if="!isLoading" class="text-center py-12">
      <Icon
        name="i-heroicons-chat-bubble-left-right"
        class="w-16 h-16 text-gray-400 dark:text-gray-500 mx-auto mb-4"
      />
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        No conversations yet
      </h3>
      <p class="text-gray-500 dark:text-gray-400 mb-4">
        Start a new conversation using the chat widget in the bottom left corner
      </p>
      <UButton color="primary" icon="i-heroicons-plus" @click="startNewConversation">
        Start New Conversation
      </UButton>
    </div>

    <!-- Selected Conversation View -->
    <div v-if="selectedConversationId" class="mt-6">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Conversation</h2>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="selectedConversationId = null"
            >
              Close
            </UButton>
          </div>
        </template>

        <div class="space-y-4 max-h-[600px] overflow-y-auto">
          <div
            v-for="message in conversationMessages"
            :key="message.id"
            class="flex gap-3"
            :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[80%] rounded-lg px-4 py-2"
              :class="
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : message.role === 'system'
                    ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              "
            >
              <div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
              
              <!-- Tool Calls -->
              <div
                v-if="message.toolCalls && message.toolCalls.length > 0"
                class="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600"
              >
                <div class="text-xs font-semibold mb-1">Tool Calls:</div>
                <div
                  v-for="toolCall in message.toolCalls"
                  :key="toolCall.id"
                  class="text-xs bg-gray-200 dark:bg-gray-600 rounded p-2 mb-1"
                >
                  <div class="font-mono font-semibold">{{ toolCall.name }}</div>
                  <div class="text-gray-500 dark:text-gray-400 mt-1 text-xs">
                    Arguments:
                  </div>
                  <div class="text-gray-600 dark:text-gray-300 mt-0.5 break-all font-mono text-xs">
                    {{ JSON.stringify(toolCall.arguments, null, 2) }}
                  </div>
                  <!-- Show tool result if available -->
                  <div
                    v-if="message.toolResults && message.toolResults.find(tr => tr.callId === toolCall.id)"
                    class="mt-2 pt-2 border-t border-gray-300 dark:border-gray-500"
                  >
                    <div class="text-gray-500 dark:text-gray-400 text-xs mb-0.5">
                      Result:
                    </div>
                    <div class="text-gray-700 dark:text-gray-200 mt-0.5 break-all font-mono text-xs max-h-32 overflow-auto">
                      {{ JSON.stringify(message.toolResults.find(tr => tr.callId === toolCall.id)?.result, null, 2) }}
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="text-xs opacity-70 mt-2 flex items-center justify-between">
                <span>{{ formatTime(message.timestamp) }}</span>
                <span v-if="message.role === 'assistant' && message.model" class="text-xs opacity-60">
                  {{ message.model }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { chatService, type ChatMessage } from '~/services/chat'

definePageMeta({
  layout: 'dashboard',
})

const conversations = ref<Array<{ id: string; title: string; updatedAt: Date }>>([])
const selectedConversationId = ref<string | null>(null)
const conversationMessages = ref<ChatMessage[]>([])
const isLoading = ref(false)

const formatDate = (date: Date | string | null | undefined) => {
  if (!date) return 'No date'
  const d = typeof date === 'string' ? new Date(date) : date
  if (isNaN(d.getTime())) return 'Invalid date'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

const formatTime = (date: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const loadConversations = async () => {
  isLoading.value = true
  try {
    const result = await chatService.listConversations()
    conversations.value = result || []
  } catch (error) {
    console.error('❌ Failed to load conversations:', error)
    conversations.value = []
  } finally {
    isLoading.value = false
  }
}

const loadConversation = async (conversationId: string) => {
  selectedConversationId.value = conversationId
  isLoading.value = true
  try {
    const messages = await chatService.getConversationHistory(conversationId)
    conversationMessages.value = messages || []
  } catch (error) {
    console.error('Failed to load conversation:', error)
    conversationMessages.value = []
  } finally {
    isLoading.value = false
  }
}

const deleteConversation = async (conversationId: string) => {
  if (!confirm('Are you sure you want to delete this conversation?')) {
    return
  }
  // TODO: Implement delete endpoint
  console.log('Delete conversation:', conversationId)
  await loadConversations()
  if (selectedConversationId.value === conversationId) {
    selectedConversationId.value = null
  }
}

const startNewConversation = () => {
  // Open chat widget - this would need to be implemented via a store or event
  // For now, just scroll to top and show message
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  loadConversations()
})
</script>

