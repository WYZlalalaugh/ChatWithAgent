// 机器人相关类型
export interface Bot {
  id: string
  name: string
  description?: string
  avatar_url?: string
  user_id: string
  platform_type: string
  platform_config: Record<string, any>
  llm_config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BotCreateForm {
  name: string
  description?: string
  avatar_url?: string
  platform_type: string
  platform_config: Record<string, any>
  llm_config: Record<string, any>
}

export interface BotUpdateForm {
  name?: string
  description?: string
  avatar_url?: string
  platform_config?: Record<string, any>
  llm_config?: Record<string, any>
  is_active?: boolean
}

export interface BotStatus {
  bot_id: string
  is_online: boolean
  last_active?: string
  message_count: number
  error_count: number
  status_details: Record<string, any>
}

// 对话相关类型
export interface Conversation {
  id: string
  title: string
  bot_id: string
  user_id: string
  platform_type: string
  platform_user_id: string
  context: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  content: string
  message_type: string
  sender_type: 'user' | 'bot'
  sender_id: string
  metadata: Record<string, any>
  created_at: string
}

// 知识库相关类型
export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  user_id: string
  vector_store_type: string
  vector_store_config: Record<string, any>
  document_count: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  knowledge_base_id: string
  title: string
  content: string
  file_type: string
  file_size: number
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface SearchRequest {
  query: string
  top_k: number
  score_threshold: number
  filters?: Record<string, any>
}

export interface SearchResult {
  document_id: string
  title: string
  content: string
  score: number
  metadata: Record<string, any>
}

// 插件相关类型
export interface Plugin {
  id: string
  name: string
  version: string
  description?: string
  author: string
  category: string
  tags: string[]
  config_schema: Record<string, any>
  default_config: Record<string, any>
  is_enabled: boolean
  is_installed: boolean
  install_time?: string
  last_used?: string
  usage_count: number
}

// 系统相关类型
export interface SystemStatus {
  status: string
  uptime: number
  memory_usage: {
    total: number
    available: number
    percent: number
    used: number
  }
  cpu_usage: number
  disk_usage: {
    total: number
    used: number
    free: number
    percent: number
  }
  active_connections: number
  active_bots: number
  total_users: number
  total_conversations: number
  total_messages: number
}

// 通用类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ListQuery {
  page?: number
  page_size?: number
  search?: string
  sort?: string
  order?: 'asc' | 'desc'
}