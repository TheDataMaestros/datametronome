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
      <Icon
        name="i-heroicons-arrow-path"
        class="w-8 h-8 text-gray-400 dark:text-gray-500 mx-auto mb-4 animate-spin"
      />
      <p class="text-gray-500 dark:text-gray-400">Loading conversations...</p>
    </div>

    <!-- Conversations List -->
    <div
      v-if="conversations.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <UCard
        v-for="conversation in conversations"
        :key="conversation.id"
        class="overflow-hidden cursor-pointer transition-all"
        :class="selectedConversationId === conversation.id ? 'ring-2 ring-primary-500' : ''"
        @click="loadConversation(conversation.id)"
      >
        <template #header>
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-semibold text-gray-900 dark:text-white truncate min-w-0">
              {{ conversation.title }}
            </h3>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-trash"
              size="xs"
              class="shrink-0"
              :aria-label="`Delete conversation ${conversation.title}`"
              @click.prevent.stop="openDeleteConfirm(conversation)"
            />
          </div>
        </template>

        <div class="text-sm text-gray-500 dark:text-gray-400">
          <div class="flex items-center gap-2">
            <Icon name="i-heroicons-clock" class="w-4 h-4 shrink-0" />
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
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">No conversations yet</h3>
      <p class="text-gray-500 dark:text-gray-400 mb-4">
        Type a message below to start your first conversation
      </p>
    </div>

    <!-- Delete confirmation modal -->
    <UModal v-model="showDeleteModal" :ui="{ width: 'sm:max-w-md' }">
      <div class="p-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Delete conversation?
        </h3>
        <p class="text-gray-600 dark:text-gray-400 mb-4">
          This will permanently remove this conversation. This cannot be undone.
        </p>
        <p v-if="deleteError" class="text-sm text-red-600 dark:text-red-400 mb-3">
          {{ deleteError }}
        </p>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="outline" @click="showDeleteModal = false">
            Cancel
          </UButton>
          <UButton color="red" :loading="isDeleting" @click="confirmDelete"> Delete </UButton>
        </div>
      </div>
    </UModal>

    <!-- New Conversation / Selected Conversation View -->
    <div ref="conversationPanel" class="mt-6">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
              {{ selectedConversationId ? 'Conversation' : 'New Conversation' }}
            </h2>
            <div class="flex items-center gap-2">
              <UButton
                v-if="selectedConversationId"
                color="primary"
                variant="ghost"
                icon="i-heroicons-chat-bubble-left-right"
                @click="continueInWidget"
              >
                Continue in Chat Widget
              </UButton>
              <!-- Share / copy URL button -->
              <UButton
                v-if="selectedConversationId"
                color="gray"
                variant="ghost"
                icon="i-heroicons-link"
                :title="copyLinkLabel"
                @click="copyConversationLink"
              >
                {{ copyLinkLabel }}
              </UButton>
              <UButton
                v-if="selectedConversationId"
                color="gray"
                variant="ghost"
                icon="i-heroicons-x-mark"
                @click="startNewConversation"
              >
                Close
              </UButton>
            </div>
          </div>
        </template>

        <div class="space-y-4">
          <!-- Messages Area -->
          <div
            v-if="conversationMessages.length > 0 || isSending"
            ref="messagesContainer"
            class="max-h-[600px] overflow-y-auto space-y-4"
          >
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
                    <div class="text-gray-500 dark:text-gray-400 mt-1 text-xs">Arguments:</div>
                    <div
                      class="text-gray-600 dark:text-gray-300 mt-0.5 break-all font-mono text-xs"
                    >
                      {{ JSON.stringify(toolCall.arguments, null, 2) }}
                    </div>
                    <div
                      v-if="
                        message.toolResults &&
                        message.toolResults.find((tr) => tr.callId === toolCall.id)
                      "
                      class="mt-2 pt-2 border-t border-gray-300 dark:border-gray-500"
                    >
                      <div class="text-gray-500 dark:text-gray-400 text-xs mb-0.5">Result:</div>
                      <div
                        class="text-gray-700 dark:text-gray-200 mt-0.5 break-all font-mono text-xs max-h-32 overflow-auto"
                      >
                        {{
                          JSON.stringify(
                            message.toolResults.find((tr) => tr.callId === toolCall.id)?.result,
                            null,
                            2,
                          )
                        }}
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  class="text-xs opacity-70 mt-2 flex flex-wrap items-center justify-between gap-x-2 gap-y-1"
                >
                  <span>{{ formatTime(message.timestamp) }}</span>
                  <span
                    v-if="
                      message.role === 'assistant' &&
                      (message.model || message.intent || message.agentType)
                    "
                    class="flex flex-wrap items-center gap-1 text-xs opacity-60"
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
                    <span v-if="message.model">{{ message.model }}</span>
                  </span>
                </div>
              </div>
            </div>

            <!-- Typing indicator: shown while waiting for AI response -->
            <div v-if="isSending" class="flex gap-3 justify-start">
              <div class="rounded-lg px-4 py-3 bg-gray-100 dark:bg-gray-700">
                <div class="flex items-center gap-1.5">
                  <span class="typing-dot" />
                  <span class="typing-dot" />
                  <span class="typing-dot" />
                </div>
              </div>
            </div>
          </div>

          <div v-else class="py-12 text-center text-gray-500 dark:text-gray-400">
            <Icon
              name="i-heroicons-chat-bubble-left-ellipsis"
              class="w-10 h-10 mx-auto mb-2 opacity-50"
            />
            <p class="text-sm">Type a message below to start the conversation</p>
          </div>

          <!-- Chat Input -->
          <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
            <form @submit.prevent="sendMessage" class="flex gap-2">
              <UInput
                v-model="inputMessage"
                :placeholder="
                  selectedConversationId
                    ? 'Type your message to continue the conversation...'
                    : 'Type your message to start a new conversation...'
                "
                :disabled="isSending"
                class="flex-1"
                size="lg"
              />
              <UButton
                v-if="!isSending"
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
                @click="stopRequest"
                size="lg"
              >
                Stop
              </UButton>
            </form>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { extractErrorMessage } from '~/services/api'
import { chatService, type ChatMessage } from '~/services/chat'

const router = useRouter()
const route = useRoute()

const conversations = ref<Array<{ id: string; title: string; updatedAt: Date }>>([])
const selectedConversationId = ref<string | null>(null)
const showDeleteModal = ref(false)
const isDeleting = ref(false)
const deleteError = ref<string | null>(null)
const conversationToDelete = ref<{ id: string; title: string } | null>(null)
const conversationMessages = ref<ChatMessage[]>([])
const isLoading = ref(false)
const isSending = ref(false)
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const conversationPanel = ref<HTMLElement | null>(null)
const copyLinkLabel = ref('Copy link')

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

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const scrollToConversationPanel = () => {
  nextTick(() => {
    if (conversationPanel.value) {
      conversationPanel.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
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

const loadConversationMessages = async (conversationId: string) => {
  isLoading.value = true
  try {
    const messages = await chatService.getConversationHistory(conversationId)
    conversationMessages.value = messages || []
    scrollToConversationPanel()
    nextTick(() => scrollToBottom())
  } catch (error) {
    console.error('Failed to load conversation:', error)
    conversationMessages.value = []
  } finally {
    isLoading.value = false
  }
}

const loadConversation = async (conversationId: string) => {
  selectedConversationId.value = conversationId
  inputMessage.value = ''

  // Update URL to make this conversation shareable
  if (route.params.id !== conversationId) {
    router.push('/chat/' + conversationId)
  }

  await loadConversationMessages(conversationId)
}

// Handle browser back/forward navigation and direct URL access
watch(
  () => route.params.id,
  async (newId) => {
    const id = typeof newId === 'string' ? newId : null
    if (id && id !== selectedConversationId.value) {
      selectedConversationId.value = id
      inputMessage.value = ''
      await loadConversationMessages(id)
    } else if (!id && selectedConversationId.value) {
      selectedConversationId.value = null
      conversationMessages.value = []
      inputMessage.value = ''
    }
  },
)

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isSending.value) return

  const messageContent = inputMessage.value.trim()
  inputMessage.value = ''

  const userMessage: ChatMessage = {
    id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    role: 'user',
    content: messageContent,
    timestamp: new Date(),
  }
  conversationMessages.value.push(userMessage)

  isSending.value = true
  scrollToBottom()

  try {
    const response = await chatService.sendMessage({
      message: messageContent,
      conversationId: selectedConversationId.value || undefined,
    })

    if (!selectedConversationId.value && response.conversationId) {
      selectedConversationId.value = response.conversationId
      // Update URL now that we have the new conversation ID
      router.replace('/chat/' + response.conversationId)
    }

    const assistantMessage: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role: 'assistant',
      content: response.message,
      timestamp: new Date(),
      toolCalls: response.toolCalls,
      model: response.model,
      intent: response.intent,
      agentType: response.agentType,
      orchestrationMode: response.orchestrationMode,
      agentChain: response.agentChain,
    }
    conversationMessages.value.push(assistantMessage)

    await loadConversations()
  } catch (error) {
    console.error('Failed to send message:', error)
    const errorMessage: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role: 'system',
      content: `Error: ${extractErrorMessage(error, 'Failed to send message')}`,
      timestamp: new Date(),
    }
    conversationMessages.value.push(errorMessage)
  } finally {
    isSending.value = false
    scrollToBottom()
  }
}

const stopRequest = () => {
  chatService.cancelRequest()
  isSending.value = false
}

const startNewConversation = () => {
  selectedConversationId.value = null
  conversationMessages.value = []
  inputMessage.value = ''
  if (route.path !== '/chat') {
    router.push('/chat')
  }
}

const copyConversationLink = async () => {
  const url = `${window.location.origin}/chat/${selectedConversationId.value}`
  try {
    await navigator.clipboard.writeText(url)
    copyLinkLabel.value = 'Copied!'
    setTimeout(() => {
      copyLinkLabel.value = 'Copy link'
    }, 2000)
  } catch {
    // Fallback for browsers without clipboard API
    copyLinkLabel.value = 'Copy link'
  }
}

const continueInWidget = () => {
  if (selectedConversationId.value) {
    window.dispatchEvent(
      new CustomEvent('chat:load-conversation', {
        detail: { conversationId: selectedConversationId.value },
      }),
    )
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }
}

const openDeleteConfirm = (conversation: { id: string; title: string }) => {
  conversationToDelete.value = conversation
  deleteError.value = null
  showDeleteModal.value = true
}

const confirmDelete = async () => {
  if (!conversationToDelete.value) return
  const conversationId = conversationToDelete.value.id
  isDeleting.value = true
  deleteError.value = null
  try {
    await chatService.deleteConversation(conversationId)
    showDeleteModal.value = false
    conversationToDelete.value = null
    await loadConversations()
    if (selectedConversationId.value === conversationId) {
      startNewConversation()
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
    deleteError.value = extractErrorMessage(error, 'Failed to delete conversation')
  } finally {
    isDeleting.value = false
  }
}

onMounted(async () => {
  await loadConversations()
  // Auto-load conversation if URL has an ID (direct link or page refresh)
  const id = route.params.id as string
  if (id) {
    selectedConversationId.value = id
    await loadConversationMessages(id)
  }
})
</script>

<style scoped>
.typing-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: rgb(156 163 175); /* gray-400 */
  animation: typing-bounce 1.2s ease-in-out infinite;
}

.dark .typing-dot {
  background-color: rgb(107 114 128); /* gray-500 */
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}
.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}
.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.6;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}
</style>
