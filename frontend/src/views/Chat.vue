<template>
  <div class="chat-page">
    <!-- 对话头部 -->
    <div class="chat-header">
      <div class="chat-header-left">
        <el-avatar :src="botInfo?.avatar_url" :size="40">
          {{ botInfo?.name?.charAt(0) }}
        </el-avatar>
        <div class="chat-info">
          <h3>{{ conversationTitle }}</h3>
          <span class="chat-status" :class="connectionStatus">
            {{ getStatusText() }}
          </span>
        </div>
      </div>
      <div class="chat-header-right">
        <el-button
          type="primary"
          :icon="connectionStatus === 'connected' ? 'VideoPause' : 'VideoPlay'"
          @click="toggleConnection"
        >
          {{ connectionStatus === 'connected' ? '断开' : '连接' }}
        </el-button>
        <el-button icon="Setting" @click="showSettings = true">设置</el-button>
      </div>
    </div>

    <!-- 对话消息区域 -->
    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message-item"
        :class="message.sender_type"
      >
        <div class="message-avatar">
          <el-avatar 
            v-if="message.sender_type === 'user'" 
            :src="userInfo?.avatar_url" 
            :size="32"
          >
            {{ userInfo?.nickname?.charAt(0) || 'U' }}
          </el-avatar>
          <el-avatar 
            v-else 
            :src="botInfo?.avatar_url" 
            :size="32"
          >
            {{ botInfo?.name?.charAt(0) || 'B' }}
          </el-avatar>
        </div>
        <div class="message-content">
          <div class="message-header">
            <span class="sender-name">
              {{ message.sender_type === 'user' ? userInfo?.nickname : botInfo?.name }}
            </span>
            <span class="message-time">
              {{ formatTime(message.timestamp) }}
            </span>
          </div>
          <div 
            class="message-text"
            :class="{ 'typing': message.isTyping }"
            v-html="formatMessage(message.content)"
          ></div>
        </div>
      </div>
      
      <!-- 正在输入指示器 -->
      <div v-if="isTyping" class="message-item bot typing-indicator">
        <div class="message-avatar">
          <el-avatar :src="botInfo?.avatar_url" :size="32">
            {{ botInfo?.name?.charAt(0) || 'B' }}
          </el-avatar>
        </div>
        <div class="message-content">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <div class="input-container">
        <el-input
          v-model="currentMessage"
          type="textarea"
          :rows="3"
          placeholder="输入消息..."
          @keydown.enter.exact="handleEnterKey"
          @keydown.ctrl.enter="sendMessage"
          :disabled="connectionStatus !== 'connected' || isSending"
        />
        <div class="input-actions">
          <el-button
            type="primary"
            :loading="isSending"
            :disabled="!currentMessage.trim() || connectionStatus !== 'connected'"
            @click="sendMessage"
          >
            发送 (Ctrl+Enter)
          </el-button>
        </div>
      </div>
    </div>

    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="对话设置"
      width="500px"
    >
      <el-form :model="chatSettings" label-width="100px">
        <el-form-item label="流式输出">
          <el-switch v-model="chatSettings.streamOutput" />
        </el-form-item>
        <el-form-item label="自动滚动">
          <el-switch v-model="chatSettings.autoScroll" />
        </el-form-item>
        <el-form-item label="消息音效">
          <el-switch v-model="chatSettings.soundEnabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { conversationApi } from '@/api/conversation'
import { botApi } from '@/api/bot'

interface Message {
  id: string
  content: string
  sender_type: 'user' | 'bot'
  timestamp: string
  isTyping?: boolean
}

interface ChatSettings {
  streamOutput: boolean
  autoScroll: boolean
  soundEnabled: boolean
}

// 路由和状态管理
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 响应式数据
const messages = ref<Message[]>([])
const currentMessage = ref('')
const isTyping = ref(false)
const isSending = ref(false)
const showSettings = ref(false)
const conversationTitle = ref('新对话')
const botInfo = ref<any>(null)
const userInfo = ref(authStore.user)

// WebSocket 连接
const ws = ref<WebSocket | null>(null)
const connectionStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')

// 对话设置
const chatSettings = reactive<ChatSettings>({
  streamOutput: true,
  autoScroll: true,
  soundEnabled: false
})

// DOM 引用
const messagesContainer = ref<HTMLElement>()

// 计算属性和方法
const conversationId = route.params.id as string
const botId = route.query.bot_id as string

// 获取状态文本
const getStatusText = () => {
  switch (connectionStatus.value) {
    case 'connected':
      return '已连接'
    case 'connecting':
      return '连接中...'
    case 'error':
      return '连接错误'
    default:
      return '未连接'
  }
}

// 格式化时间
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

// 格式化消息内容
const formatMessage = (content: string) => {
  // 处理换行符
  return content.replace(/\n/g, '<br>')
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatSettings.autoScroll && messagesContainer.value) {
    nextTick(() => {
      messagesContainer.value!.scrollTop = messagesContainer.value!.scrollHeight
    })
  }
}

// 建立 WebSocket 连接
const connectWebSocket = () => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    return
  }

  connectionStatus.value = 'connecting'
  
  const token = localStorage.getItem('token')
  const wsUrl = `ws://localhost:8000/api/v1/ws/chat?token=${token}&conversation_id=${conversationId}&bot_id=${botId}`
  
  ws.value = new WebSocket(wsUrl)
  
  ws.value.onopen = () => {
    connectionStatus.value = 'connected'
    ElMessage.success('WebSocket 连接成功')
  }
  
  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWebSocketMessage(data)
  }
  
  ws.value.onerror = () => {
    connectionStatus.value = 'error'
    ElMessage.error('WebSocket 连接失败')
  }
  
  ws.value.onclose = () => {
    connectionStatus.value = 'disconnected'
    ElMessage.warning('WebSocket 连接已断开')
  }
}

// 断开 WebSocket 连接
const disconnectWebSocket = () => {
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
  connectionStatus.value = 'disconnected'
}

// 切换连接状态
const toggleConnection = () => {
  if (connectionStatus.value === 'connected') {
    disconnectWebSocket()
  } else {
    connectWebSocket()
  }
}

// 处理 WebSocket 消息
const handleWebSocketMessage = (data: any) => {
  switch (data.type) {
    case 'connected':
      console.log('WebSocket 已连接:', data)
      break
      
    case 'conversation_created':
      console.log('对话已创建:', data)
      break
      
    case 'message_received':
      // 添加用户消息到界面
      messages.value.push({
        id: Date.now().toString(),
        content: data.content,
        sender_type: 'user',
        timestamp: data.timestamp
      })
      scrollToBottom()
      break
      
    case 'response_start':
      isTyping.value = true
      // 添加空的机器人消息占位符
      messages.value.push({
        id: data.stream_id,
        content: '',
        sender_type: 'bot',
        timestamp: new Date().toISOString(),
        isTyping: true
      })
      scrollToBottom()
      break
      
    case 'content':
      // 更新机器人消息内容
      const message = messages.value.find(m => m.isTyping && m.sender_type === 'bot')
      if (message) {
        message.content += data.content
        scrollToBottom()
      }
      break
      
    case 'response_complete':
      isTyping.value = false
      // 移除正在输入状态
      const completedMessage = messages.value.find(m => m.isTyping && m.sender_type === 'bot')
      if (completedMessage) {
        completedMessage.isTyping = false
      }
      isSending.value = false
      break
      
    case 'error':
      ElMessage.error(data.message || '发生错误')
      isTyping.value = false
      isSending.value = false
      break
      
    default:
      console.log('未知消息类型:', data)
  }
}

// 发送消息
const sendMessage = () => {
  const message = currentMessage.value.trim()
  if (!message || !ws.value || ws.value.readyState !== WebSocket.OPEN) {
    return
  }
  
  isSending.value = true
  
  ws.value.send(JSON.stringify({
    type: 'chat',
    content: message
  }))
  
  currentMessage.value = ''
}

// 处理回车键
const handleEnterKey = (event: KeyboardEvent) => {
  if (!event.ctrlKey) {
    event.preventDefault()
    sendMessage()
  }
}

// 加载对话历史
const loadConversationHistory = async () => {
  try {
    if (conversationId && conversationId !== 'new') {
      const conversation = await conversationApi.getConversation(conversationId)
      conversationTitle.value = conversation.title
      
      // 加载消息历史
      const messagesData = await conversationApi.getMessages(conversationId)
      messages.value = messagesData.messages.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        sender_type: msg.sender_type,
        timestamp: msg.created_at
      }))
      
      scrollToBottom()
    }
  } catch (error) {
    console.error('加载对话历史失败:', error)
  }
}

// 加载机器人信息
const loadBotInfo = async () => {
  try {
    if (botId) {
      botInfo.value = await botApi.getBot(botId)
      if (!conversationTitle.value || conversationTitle.value === '新对话') {
        conversationTitle.value = `与 ${botInfo.value.name} 的对话`
      }
    }
  } catch (error) {
    console.error('加载机器人信息失败:', error)
  }
}

// 保存设置
const saveSettings = () => {
  localStorage.setItem('chatSettings', JSON.stringify(chatSettings))
  showSettings.value = false
  ElMessage.success('设置已保存')
}

// 加载设置
const loadSettings = () => {
  const saved = localStorage.getItem('chatSettings')
  if (saved) {
    Object.assign(chatSettings, JSON.parse(saved))
  }
}

// 监听消息变化自动滚动
watch(messages, scrollToBottom, { deep: true })

// 生命周期钩子
onMounted(async () => {
  loadSettings()
  await loadBotInfo()
  await loadConversationHistory()
  connectWebSocket()
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-color-page);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-color);
  border-bottom: 1px solid var(--border-color);
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-info h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-color-primary);
}

.chat-status {
  font-size: 12px;
  color: var(--text-color-secondary);
}

.chat-status.connected {
  color: var(--success-color);
}

.chat-status.error {
  color: var(--danger-color);
}

.chat-header-right {
  display: flex;
  gap: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.user .message-content {
  background: var(--primary-color);
  color: white;
  text-align: right;
}

.message-item.bot .message-content {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
}

.message-content {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sender-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.message-time {
  font-size: 11px;
  color: var(--text-color-placeholder);
}

.message-text {
  line-height: 1.5;
  word-wrap: break-word;
}

.typing-indicator .typing-dots {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-color-secondary);
  animation: typing 1.4s infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  30% {
    transform: scale(1.2);
    opacity: 1;
  }
}

.chat-input {
  padding: 16px;
  background: var(--bg-color);
  border-top: 1px solid var(--border-color);
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .message-item {
    max-width: 95%;
  }
  
  .chat-header {
    padding: 12px;
  }
  
  .chat-messages {
    padding: 12px;
  }
  
  .chat-input {
    padding: 12px;
  }
}
</style>