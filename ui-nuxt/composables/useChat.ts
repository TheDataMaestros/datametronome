import { ref, readonly } from 'vue'
import { chatService, type ChatMessage, type ChatRequest, type ToolCall } from '~/services/chat'

export const useChat = () => {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const conversationId = ref<string | null>(null)
  const isStreaming = ref(false)
  const abortController = ref<AbortController | null>(null)

  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
    }
    messages.value.push(newMessage)
    return newMessage
  }

  const sendMessage = async (content: string, context?: Record<string, any>) => {
    isLoading.value = true
    error.value = null

    // Create abort controller for this request
    abortController.value = new AbortController()

    // Add user message
    const userMessage = addMessage({
      role: 'user',
      content,
    })

    try {
      const request: ChatRequest = {
        message: content,
        conversationId: conversationId.value || undefined,
        context,
      }

      const response = await chatService.sendMessage(request, abortController.value.signal)

      // Update conversation ID if provided
      if (response.conversationId) {
        conversationId.value = response.conversationId
      }

      // Add assistant message
      const assistantMessage = addMessage({
        role: 'assistant',
        content: response.message,
        toolCalls: response.toolCalls,
      })

      return assistantMessage
    } catch (err) {
      // Don't show error if request was aborted
      if (err instanceof Error && err.name === 'AbortError') {
        error.value = 'Request cancelled'
        // Add cancellation message
        addMessage({
          role: 'system',
          content: 'Request cancelled by user',
        })
      } else {
        error.value = err instanceof Error ? err.message : 'Failed to send message'
        console.error('Error sending chat message:', err)

        // Add error message
        addMessage({
          role: 'system',
          content: `Error: ${error.value}`,
        })
      }

      throw err
    } finally {
      isLoading.value = false
      abortController.value = null
    }
  }

  const stopRequest = () => {
    if (abortController.value) {
      abortController.value.abort()
      chatService.cancelRequest()
      isLoading.value = false
      abortController.value = null
    }
  }

  const clearMessages = () => {
    messages.value = []
    conversationId.value = null
    error.value = null
  }

  const loadConversation = async (id: string) => {
    isLoading.value = true
    error.value = null

    try {
      const history = await chatService.getConversationHistory(id)
      messages.value = history
      conversationId.value = id
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load conversation'
      console.error('Error loading conversation:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    messages: readonly(messages),
    isLoading: readonly(isLoading),
    error: readonly(error),
    conversationId: readonly(conversationId),
    isStreaming: readonly(isStreaming),
    sendMessage,
    stopRequest,
    clearMessages,
    loadConversation,
    addMessage,
  }
}
