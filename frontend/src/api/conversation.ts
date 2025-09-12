// 对话管理 API
import { request } from './request'

export interface Conversation {
  id: string
  user_id: string
  bot_id: string
  title: string
  platform: string
  platform_chat_id: string
  status: string
  context: Record<string, any>
  created_at: string
  updated_at: string
  last_message_at?: string
}

export interface Message {
  id: string
  conversation_id: string
  content: string
  message_type: string
  sender_type: string
  sender_id: string
  metadata: Record<string, any>
  created_at: string
}

export interface ConversationListResponse {
  conversations: Conversation[]
  total: number
  page: number
  page_size: number
}

export interface MessageListResponse {
  messages: Message[]
  total: number
  page: number
  page_size: number
}

export interface ChatRequest {
  message: string
  stream?: boolean
  context?: Record<string, any>
}

export interface ChatResponse {
  message_id: string
  response: string
  conversation_id: string
  timestamp: string
}

export const conversationApi = {
  // 获取对话列表
  async getConversations(params?: {
    page?: number
    page_size?: number
    bot_id?: string
    platform?: string
    status?: string
  }): Promise<ConversationListResponse> {
    return request.get('/conversations/', { params })
  },

  // 获取对话详情
  async getConversation(id: string): Promise<Conversation> {
    return request.get(`/conversations/${id}`)
  },

  // 创建对话
  async createConversation(data: {
    bot_id: string
    title?: string
    platform?: string
    platform_chat_id?: string
    context?: Record<string, any>
  }): Promise<Conversation> {
    return request.post('/conversations/', data)
  },

  // 更新对话
  async updateConversation(
    id: string,
    data: {
      title?: string
      context?: Record<string, any>
    }
  ): Promise<Conversation> {
    return request.put(`/conversations/${id}`, data)
  },

  // 删除对话
  async deleteConversation(id: string): Promise<{ success: boolean; message: string }> {
    return request.delete(`/conversations/${id}`)
  },

  // 获取对话消息
  async getMessages(conversationId: string, params?: {
    page?: number
    page_size?: number
    message_type?: string
    sender_type?: string
  }): Promise<MessageListResponse> {
    return request.get('/messages/', {
      params: {
        conversation_id: conversationId,
        ...params
      }
    })
  },

  // 发送消息（非流式）
  async sendMessage(conversationId: string, data: ChatRequest): Promise<ChatResponse> {
    return request.post(`/conversations/${conversationId}/chat`, data)
  },

  // 发送消息（流式）
  async sendMessageStream(conversationId: string, data: ChatRequest): Promise<ReadableStream> {
    const response = await fetch(`/api/v1/conversations/${conversationId}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error('Stream request failed')
    }

    return response.body!
  },

  // 获取对话统计
  async getConversationStatistics(conversationId: string): Promise<{
    conversation_id: string
    total_messages: number
    user_messages: number
    bot_messages: number
    avg_response_time: number
    first_message_time?: string
    last_message_time?: string
    conversation_duration: number
  }> {
    return request.get(`/conversations/${conversationId}/statistics`)
  }
}

export default conversationApi