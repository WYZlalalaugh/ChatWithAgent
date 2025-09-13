<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">对话详情</h1>
      <div class="page-actions">
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="enterChat">进入聊天</el-button>
      </div>
    </div>

    <div v-loading="loading" class="conversation-detail">
      <!-- 对话信息卡片 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>对话信息</span>
            <el-tag :type="getStatusTagType(conversationInfo?.status)">
              {{ getStatusText(conversationInfo?.status) }}
            </el-tag>
          </div>
        </template>
        
        <div class="conversation-info">
          <div class="info-item">
            <label>对话标题：</label>
            <span>{{ conversationInfo?.title }}</span>
          </div>
          
          <div class="info-item">
            <label>关联机器人：</label>
            <el-tag type="primary">{{ conversationInfo?.bot_name }}</el-tag>
          </div>
          
          <div class="info-item">
            <label>参与者：</label>
            <div class="participants">
              <el-tag
                v-for="user in conversationInfo?.participants"
                :key="user.id"
                size="small"
                style="margin-right: 8px;"
              >
                {{ user.nickname }}
              </el-tag>
            </div>
          </div>
          
          <div class="info-item">
            <label>消息总数：</label>
            <span>{{ conversationInfo?.message_count }}</span>
          </div>
          
          <div class="info-item">
            <label>创建时间：</label>
            <span>{{ formatTime(conversationInfo?.created_at) }}</span>
          </div>
          
          <div class="info-item">
            <label>最后更新：</label>
            <span>{{ formatTime(conversationInfo?.last_message_at) }}</span>
          </div>
        </div>
      </el-card>

      <!-- 消息历史 -->
      <el-card class="messages-card">
        <template #header>
          <div class="card-header">
            <span>消息历史</span>
            <div class="message-actions">
              <el-button size="small" @click="refreshMessages">刷新</el-button>
              <el-button size="small" @click="exportMessages">导出</el-button>
            </div>
          </div>
        </template>
        
        <div class="messages-container" ref="messagesContainer">
          <div
            v-for="message in messages"
            :key="message.id"
            class="message-item"
            :class="message.sender_type"
          >
            <div class="message-avatar">
              <el-avatar :src="message.sender_avatar" :size="32">
                {{ message.sender_name?.charAt(0) }}
              </el-avatar>
            </div>
            
            <div class="message-content">
              <div class="message-header">
                <span class="sender-name">{{ message.sender_name }}</span>
                <span class="message-time">{{ formatTime(message.created_at) }}</span>
              </div>
              
              <div class="message-text" v-html="formatMessage(message.content)"></div>
              
              <div v-if="message.attachments && message.attachments.length" class="message-attachments">
                <el-tag
                  v-for="attachment in message.attachments"
                  :key="attachment.id"
                  size="small"
                  type="info"
                  style="margin-right: 8px;"
                >
                  {{ attachment.filename }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="messagePagination.page"
            v-model:page-size="messagePagination.pageSize"
            :total="messagePagination.total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleMessageSizeChange"
            @current-change="handleMessageCurrentChange"
          />
        </div>
      </el-card>

      <!-- 统计信息 -->
      <el-card class="stats-card">
        <template #header>
          <span>统计信息</span>
        </template>
        
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">总消息数</div>
            <div class="stat-value">{{ conversationInfo?.message_count || 0 }}</div>
          </div>
          
          <div class="stat-item">
            <div class="stat-label">用户消息</div>
            <div class="stat-value">{{ userMessageCount }}</div>
          </div>
          
          <div class="stat-item">
            <div class="stat-label">机器人回复</div>
            <div class="stat-value">{{ botMessageCount }}</div>
          </div>
          
          <div class="stat-item">
            <div class="stat-label">对话时长</div>
            <div class="stat-value">{{ conversationDuration }}</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

// 数据状态
const loading = ref(false)
const conversationInfo = ref<any>(null)
const messages = ref([])

// 对话ID
const conversationId = route.params.id as string

// 消息分页
const messagePagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 计算属性
const userMessageCount = computed(() => {
  return messages.value.filter((msg: any) => msg.sender_type === 'user').length
})

const botMessageCount = computed(() => {
  return messages.value.filter((msg: any) => msg.sender_type === 'bot').length
})

const conversationDuration = computed(() => {
  if (!conversationInfo.value?.created_at || !conversationInfo.value?.last_message_at) {
    return '-'
  }
  
  const start = dayjs(conversationInfo.value.created_at)
  const end = dayjs(conversationInfo.value.last_message_at)
  const diff = end.diff(start, 'minute')
  
  if (diff < 60) {
    return `${diff} 分钟`
  } else if (diff < 1440) {
    return `${Math.floor(diff / 60)} 小时 ${diff % 60} 分钟`
  } else {
    return `${Math.floor(diff / 1440)} 天`
  }
})

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const types = {
    active: 'success',
    archived: 'info',
    deleted: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts = {
    active: '进行中',
    archived: '已归档',
    deleted: '已删除'
  }
  return texts[status] || status
}

// 格式化时间
const formatTime = (time: string) => {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 格式化消息内容
const formatMessage = (content: string) => {
  // 处理换行符
  return content.replace(/\n/g, '<br>')
}

// 进入聊天
const enterChat = () => {
  router.push(`/chat/${conversationId}`)
}

// 刷新消息
const refreshMessages = () => {
  loadMessages()
}

// 导出消息
const exportMessages = () => {
  ElMessage.info('导出功能开发中...')
}

// 消息分页处理
const handleMessageSizeChange = (size: number) => {
  messagePagination.pageSize = size
  messagePagination.page = 1
  loadMessages()
}

const handleMessageCurrentChange = (page: number) => {
  messagePagination.page = page
  loadMessages()
}

// 加载对话信息
const loadConversationInfo = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取对话信息
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟数据
    conversationInfo.value = {
      id: conversationId,
      title: '用户咨询产品功能',
      bot_name: '客服助手',
      status: 'active',
      participants: [
        { id: '1', nickname: '张三' }
      ],
      message_count: 15,
      created_at: '2024-01-10T10:00:00Z',
      last_message_at: '2024-01-10T14:30:00Z'
    }
  } catch (error) {
    ElMessage.error('加载对话信息失败')
  } finally {
    loading.value = false
  }
}

// 加载消息历史
const loadMessages = async () => {
  try {
    // TODO: 调用API获取消息历史
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // 模拟消息数据
    messages.value = [
      {
        id: '1',
        content: '您好，我想了解一下产品的功能',
        sender_type: 'user',
        sender_name: '张三',
        sender_avatar: '',
        created_at: '2024-01-10T10:01:00Z',
        attachments: []
      },
      {
        id: '2',
        content: '您好！很高兴为您介绍我们的产品功能。我们的产品主要包括以下特点：\n1. 智能对话\n2. 知识管理\n3. 多平台支持',
        sender_type: 'bot',
        sender_name: '客服助手',
        sender_avatar: '',
        created_at: '2024-01-10T10:01:30Z',
        attachments: []
      }
    ]
    
    messagePagination.total = messages.value.length
  } catch (error) {
    ElMessage.error('加载消息失败')
  }
}

onMounted(() => {
  loadConversationInfo()
  loadMessages()
})
</script>

<style scoped>
.conversation-detail {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversation-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item label {
  font-weight: 500;
  color: var(--el-text-color-secondary);
  min-width: 100px;
}

.participants {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.message-actions {
  display: flex;
  gap: 8px;
}

.messages-container {
  max-height: 600px;
  overflow-y: auto;
  padding: 16px 0;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.message-item:hover {
  background: var(--el-bg-color-page);
}

.message-item.user {
  background: rgba(64, 158, 255, 0.1);
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sender-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.message-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.message-text {
  line-height: 1.6;
  word-wrap: break-word;
  margin-bottom: 8px;
}

.message-attachments {
  margin-top: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 16px 0;
  border-top: 1px solid var(--el-border-color);
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .message-item {
    flex-direction: column;
    gap: 8px;
  }
  
  .message-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>