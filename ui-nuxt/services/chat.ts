import { apiService } from './api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
  toolResults?: ToolResult[]
  model?: string // Model name that generated the response
  finishReason?: string // Finish reason from the model
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, any>
}

export interface ToolResult {
  callId: string
  result: any
  error?: string
}

export interface ChatRequest {
  message: string
  conversationId?: string
  context?: Record<string, any>
}

export interface ChatResponse {
  message: string
  conversationId: string
  toolCalls?: ToolCall[]
  finishReason?: string
  model?: string // Model name that generated the response
}

class ChatService {
  private readonly endpoint = '/chat'
  private abortController: AbortController | null = null

  async sendMessage(request: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
    // Create abort controller if not provided
    if (!signal) {
      this.abortController = new AbortController()
      signal = this.abortController.signal
    }

    const response = await apiService.post<ChatResponse>(this.endpoint, request, signal)
    return response.data
  }

  cancelRequest(): void {
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
  }

  async sendMessageStream(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
  ): Promise<ChatResponse> {
    // For streaming support, you might need to implement Server-Sent Events or WebSocket
    // For now, this is a placeholder for the streaming interface
    const response = await this.sendMessage(request)
    return response
  }

  async getConversationHistory(conversationId: string): Promise<ChatMessage[]> {
    const response = await apiService.get<
      Array<{
        id: string
        role: 'user' | 'assistant' | 'system'
        content: string
        timestamp: string
        toolCalls?: ToolCall[]
      }>
    >(`${this.endpoint}/conversations/${conversationId}`)
    // Convert timestamp strings to Date objects
    return response.data.map((msg) => {
      let timestamp: Date
      if (msg.timestamp) {
        try {
          timestamp = new Date(msg.timestamp)
          // Validate the date
          if (isNaN(timestamp.getTime())) {
            console.warn(`Invalid timestamp for message ${msg.id}: ${msg.timestamp}`)
            timestamp = new Date(0) // Use epoch as fallback
          }
        } catch (e) {
          console.error(`Error parsing timestamp for message ${msg.id}:`, e)
          timestamp = new Date(0) // Use epoch as fallback
        }
      } else {
        console.warn(`Missing timestamp for message ${msg.id}`)
        timestamp = new Date(0) // Use epoch as fallback
      }
      return {
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp,
        toolCalls: msg.toolCalls,
      }
    })
  }

  async listConversations(): Promise<Array<{ id: string; title: string; updatedAt: Date }>> {
    const response = await apiService.get<
      Array<{ id: string; title: string; updatedAt: string | null }>
    >(`${this.endpoint}/conversations`)
    return response.data.map((conv) => {
      // Handle null or invalid dates - use epoch instead of current time
      let updatedAt: Date
      if (conv.updatedAt) {
        updatedAt = new Date(conv.updatedAt)
        // Check if date is valid
        if (isNaN(updatedAt.getTime())) {
          console.warn(`Invalid updatedAt for conversation ${conv.id}: ${conv.updatedAt}`)
          updatedAt = new Date(0) // Use epoch (1970) instead of current date
        }
      } else {
        console.warn(`Missing updatedAt for conversation ${conv.id}`)
        updatedAt = new Date(0) // Use epoch (1970) instead of current date if null
      }
      return {
        ...conv,
        updatedAt,
      }
    })
  }
}

export const chatService = new ChatService()
