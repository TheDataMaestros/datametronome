<template>
  <!-- Chat Button (always visible) -->
  <div class="fixed bottom-6 left-6 z-50">
    <Transition name="slide-up">
      <!-- Chat Window -->
      <div
        v-if="isOpen"
        class="mb-4 w-96 h-[600px] bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden"
      >
        <!-- Chat Header -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-primary-50 dark:bg-primary-900/20"
        >
          <div class="flex items-center gap-3">
            <Icon
              name="i-heroicons-chat-bubble-left-right"
              class="w-5 h-5 text-primary-600 dark:text-primary-400"
            />
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">AI Assistant</h3>
          </div>
          <div class="flex items-center gap-2">
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-trash"
              size="xs"
              @click="handleClear"
              :disabled="chat.isLoading.value"
            />
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              size="xs"
              @click="toggleChat"
            />
          </div>
        </div>

        <!-- Messages Area -->
        <div
          ref="messagesContainer"
          class="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-50 dark:bg-gray-900/50"
        >
          <div
            v-if="chat.messages.value.length === 0"
            class="flex items-center justify-center h-full"
          >
            <div class="text-center px-4">
              <Icon
                name="i-heroicons-sparkles"
                class="w-10 h-10 text-gray-400 dark:text-gray-500 mx-auto mb-3"
              />
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Start a conversation with the AI assistant
              </p>
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-2">
                Ask questions about your data quality, checks, or get help with configuration
              </p>
            </div>
          </div>

          <div
            v-for="message in chat.messages.value"
            :key="message.id"
            class="flex gap-2"
            :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] rounded-lg px-3 py-2 text-sm"
              :class="
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : message.role === 'system'
                    ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
                    : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
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
                  <div class="text-gray-600 dark:text-gray-300 mt-1 break-all">
                    {{ JSON.stringify(toolCall.arguments, null, 2) }}
                  </div>
                </div>
              </div>

              <div class="text-xs opacity-70 mt-1 flex flex-wrap items-center gap-1">
                <span>{{ formatTime(message.timestamp) }}</span>
                <span
                  v-if="message.role === 'assistant' && (message.intent || message.agentType)"
                  class="flex flex-wrap items-center gap-1"
                >
                  <span v-if="message.intent" class="rounded bg-gray-200 dark:bg-gray-600 px-1">{{
                    message.intent
                  }}</span>
                  <span
                    v-if="message.agentType"
                    class="rounded bg-gray-200 dark:bg-gray-600 px-1"
                    >{{ message.agentType }}</span
                  >
                  <span
                    v-if="message.orchestrationMode === 'chain' && message.agentChain?.length"
                    class="rounded bg-primary-200 dark:bg-primary-800 px-1"
                    >{{ message.agentChain.join('→') }}</span
                  >
                  <span
                    v-if="message.orchestrationMode === 'parallel' && message.agentChain?.length"
                    class="rounded bg-primary-200 dark:bg-primary-800 px-1"
                    >{{ message.agentChain.join('+') }}</span
                  >
                </span>
              </div>
            </div>
          </div>

          <!-- Loading Indicator -->
          <div v-if="chat.isLoading.value" class="flex justify-start gap-2">
            <div class="bg-white dark:bg-gray-700 rounded-lg px-3 py-2 shadow-sm">
              <div class="flex items-center gap-2">
                <Icon name="i-heroicons-arrow-path" class="w-3 h-3 animate-spin" />
                <span class="text-xs text-gray-600 dark:text-gray-300">Thinking...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Error Message -->
        <div
          v-if="chat.error.value"
          class="px-3 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800"
        >
          <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
            <Icon name="i-heroicons-exclamation-circle" class="w-4 h-4" />
            <span class="text-xs">{{ chat.error.value }}</span>
          </div>
        </div>

        <!-- Input Area -->
        <div
          class="px-3 py-3 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
        >
          <form @submit.prevent="handleSubmit" class="flex gap-2">
            <UInput
              v-model="inputMessage"
              placeholder="Type your message..."
              :disabled="chat.isLoading.value"
              class="flex-1 text-sm"
              size="sm"
            />
            <UButton
              v-if="!chat.isLoading.value"
              type="submit"
              color="primary"
              icon="i-heroicons-paper-airplane"
              :disabled="!inputMessage.trim()"
              size="sm"
            />
            <UButton
              v-else
              type="button"
              color="red"
              icon="i-heroicons-stop"
              @click="chat.stopRequest()"
              size="sm"
            >
              Stop
            </UButton>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Toggle Button -->
    <UButton
      @click="toggleChat"
      :icon="isOpen ? 'i-heroicons-x-mark' : 'i-heroicons-chat-bubble-left-right'"
      color="primary"
      size="lg"
      :aria-label="isOpen ? 'Close chat' : 'Open chat'"
      :class="isOpen ? 'rounded-full' : 'rounded-full shadow-lg'"
      class="!w-14 !h-14"
    >
      <span
        v-if="!isOpen"
        class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white dark:border-gray-800"
      ></span>
    </UButton>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChat } from '~/composables/useChat'

const chat = useChat()
const isOpen = ref(false)
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const formatTime = (date: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const toggleChat = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
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
    if (isOpen.value) {
      scrollToBottom()
    }
  },
)

watch(
  () => chat.isLoading.value,
  () => {
    if (!chat.isLoading.value && isOpen.value) {
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

const handleLoadConversation = async (event: CustomEvent) => {
  const { conversationId } = event.detail
  if (conversationId) {
    // Open chat widget if not already open
    if (!isOpen.value) {
      isOpen.value = true
    }
    // Load the conversation
    try {
      await chat.loadConversation(conversationId)
      scrollToBottom()
    } catch (error) {
      console.error('Failed to load conversation in widget:', error)
    }
  }
}

onMounted(() => {
  // Auto-scroll on mount if chat is open
  if (isOpen.value) {
    scrollToBottom()
  }

  // Listen for custom event to load conversation from chat history page
  window.addEventListener('chat:load-conversation', handleLoadConversation as EventListener)
})

onUnmounted(() => {
  // Cleanup event listener
  window.removeEventListener('chat:load-conversation', handleLoadConversation as EventListener)
})
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
