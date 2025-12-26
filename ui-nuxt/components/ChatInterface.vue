<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow-lg">
    <!-- Chat Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
      <div class="flex items-center gap-3">
        <Icon name="i-heroicons-chat-bubble-left-right" class="w-6 h-6 text-primary-600" />
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">AI Assistant</h2>
      </div>
      <UButton
        color="gray"
        variant="ghost"
        icon="i-heroicons-trash"
        size="sm"
        @click="handleClear"
        :disabled="chat.isLoading.value"
      >
        Clear
      </UButton>
    </div>

    <!-- Messages Area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      <div v-if="chat.messages.value.length === 0" class="flex items-center justify-center h-full">
        <div class="text-center">
          <Icon
            name="i-heroicons-sparkles"
            class="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-4"
          />
          <p class="text-gray-500 dark:text-gray-400">
            Start a conversation with the AI assistant
          </p>
          <p class="text-sm text-gray-400 dark:text-gray-500 mt-2">
            Ask questions about your data quality, checks, or get help with configuration
          </p>
        </div>
      </div>

      <div
        v-for="message in chat.messages.value"
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
          <div class="whitespace-pre-wrap">{{ message.content }}</div>

          <!-- Tool Calls -->
          <div v-if="message.toolCalls && message.toolCalls.length > 0" class="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600">
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
              <div class="text-gray-600 dark:text-gray-300 mt-0.5 font-mono text-xs">
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
                <div class="text-gray-700 dark:text-gray-200 mt-0.5 font-mono text-xs max-h-32 overflow-auto">
                  {{ JSON.stringify(message.toolResults.find(tr => tr.callId === toolCall.id)?.result, null, 2) }}
                </div>
              </div>
            </div>
          </div>

          <div class="text-xs opacity-70 mt-1">
            {{ formatTime(message.timestamp) }}
          </div>
        </div>
      </div>

      <!-- Loading Indicator -->
      <div v-if="chat.isLoading.value" class="flex justify-start gap-3">
        <div class="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
          <div class="flex items-center gap-2">
            <Icon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
            <span class="text-sm text-gray-600 dark:text-gray-300">Thinking...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="chat.error.value" class="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800">
      <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
        <Icon name="i-heroicons-exclamation-circle" class="w-5 h-5" />
        <span class="text-sm">{{ chat.error.value }}</span>
      </div>
    </div>

    <!-- Input Area -->
    <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
      <form @submit.prevent="handleSubmit" class="flex gap-2">
        <UInput
          v-model="inputMessage"
          placeholder="Type your message..."
          :disabled="chat.isLoading.value"
          class="flex-1"
          size="lg"
        />
        <UButton
          v-if="!chat.isLoading.value"
          type="submit"
          color="primary"
          icon="i-heroicons-paper-airplane"
          :disabled="!inputMessage.trim()"
          size="lg"
        >
          Send
        </UButton>
        <UButton
          v-else
          type="button"
          color="red"
          icon="i-heroicons-stop"
          @click="chat.stopRequest()"
          size="lg"
        >
          Stop
        </UButton>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChat } from '~/composables/useChat'

const chat = useChat()
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const formatTime = (date: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(
  () => chat.messages.value.length,
  () => {
    scrollToBottom()
  },
)

watch(
  () => chat.isLoading.value,
  () => {
    if (!chat.isLoading.value) {
      scrollToBottom()
    }
  },
)

const handleSubmit = async () => {
  if (!inputMessage.value.trim() || chat.isLoading.value) {
    return
  }

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  try {
    await chat.sendMessage(message)
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

const handleClear = () => {
  if (confirm('Are you sure you want to clear the conversation?')) {
    chat.clearMessages()
  }
}
</script>

