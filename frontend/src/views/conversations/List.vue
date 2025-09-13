<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">对话管理</h1>
      <div class="page-actions">
        <el-button type="primary" :icon="Plus" @click="createConversation">
          新建对话
        </el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索对话标题..."
          :prefix-icon="Search"
          clearable
          style="width: 300px;"
          @input="handleSearch"
        />
        <el-select
          v-model="botFilter"
          placeholder="选择机器人"
          clearable
          style="width: 200px;"
          @change="handleSearch"
        >
          <el-option
            v-for="bot in bots"
            :key="bot.id"
            :label="bot.name"
            :value="bot.id"
          />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleSearch"
        />
      </div>
      <div class="toolbar-right">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
        <el-button :icon="Download" @click="exportData">导出</el-button>
      </div>
    </div>

    <!-- 对话列表 -->
    <div class="content-card">
      <el-table
        v-loading="loading"
        :data="conversationList"
        @selection-change="handleSelectionChange"
        stripe
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column label="对话信息" min-width="200">
          <template #default="{ row }">
            <div class="conversation-info">
              <div class="conversation-title">{{ row.title }}</div>
              <div class="conversation-meta">
                <el-tag size="small" type="info">{{ row.bot_name }}</el-tag>
                <span class="message-count">{{ row.message_count }} 条消息</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="参与者" width="150">
          <template #default="{ row }">
            <div class="participants">
              <el-avatar
                v-for="user in row.participants"
                :key="user.id"
                :src="user.avatar_url"
                :size="24"
                class="participant-avatar"
              >
                {{ user.nickname?.charAt(0) }}
              </el-avatar>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="最后消息" width="150">
          <template #default="{ row }">
            <div class="last-message">
              <div class="message-preview">{{ row.last_message }}</div>
              <div class="message-time">{{ formatTime(row.last_message_at) }}</div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="查看详情">
                <el-button
                  text
                  :icon="View"
                  @click="viewConversation(row)"
                />
              </el-tooltip>
              
              <el-tooltip content="进入聊天">
                <el-button
                  text
                  :icon="ChatDotRound"
                  type="primary"
                  @click="enterChat(row)"
                />
              </el-tooltip>
              
              <el-tooltip content="导出对话">
                <el-button
                  text
                  :icon="Download"
                  @click="exportConversation(row)"
                />
              </el-tooltip>
              
              <el-popconfirm
                title="确定要删除这个对话吗？"
                @confirm="deleteConversation(row)"
              >
                <template #reference>
                  <el-tooltip content="删除">
                    <el-button
                      text
                      :icon="Delete"
                      type="danger"
                    />
                  </el-tooltip>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Search,
  Refresh,
  Download,
  View,
  ChatDotRound,
  Delete
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()

// 数据状态
const loading = ref(false)
const searchQuery = ref('')
const botFilter = ref('')
const dateRange = ref([])
const selectedConversations = ref([])

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 机器人列表
const bots = ref([
  { id: '1', name: '客服助手' },
  { id: '2', name: '技术支持' },
  { id: '3', name: '销售顾问' }
])

// 对话列表数据（模拟数据）
const conversationList = ref([
  {
    id: '1',
    title: '用户咨询产品功能',
    bot_name: '客服助手',
    bot_id: '1',
    message_count: 15,
    status: 'active',
    participants: [
      { id: '1', nickname: '张三', avatar_url: '' }
    ],
    last_message: '谢谢您的解答，我明白了',
    last_message_at: '2024-01-10T14:30:00Z',
    created_at: '2024-01-10T10:00:00Z'
  },
  {
    id: '2',
    title: '技术问题咨询',
    bot_name: '技术支持',
    bot_id: '2',
    message_count: 8,
    status: 'archived',
    participants: [
      { id: '2', nickname: '李四', avatar_url: '' }
    ],
    last_message: '问题已解决',
    last_message_at: '2024-01-09T16:45:00Z',
    created_at: '2024-01-09T14:20:00Z'
  }
])

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
  return dayjs(time).format('MM-DD HH:mm')
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  loadConversations()
}

// 刷新数据
const refreshData = () => {
  loadConversations()
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedConversations.value = selection
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  loadConversations()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadConversations()
}

// 创建对话
const createConversation = () => {
  router.push('/chat/new')
}

// 查看对话详情
const viewConversation = (conversation: any) => {
  router.push(`/conversations/${conversation.id}/detail`)
}

// 进入聊天
const enterChat = (conversation: any) => {
  router.push(`/chat/${conversation.id}`)
}

// 导出对话
const exportConversation = async (conversation: any) => {
  try {
    ElMessage.info('导出功能开发中...')
    // TODO: 实现导出功能
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 导出数据
const exportData = () => {
  ElMessage.info('导出功能开发中...')
}

// 删除对话
const deleteConversation = async (conversation: any) => {
  try {
    // TODO: 调用API删除
    ElMessage.success('删除成功')
    loadConversations()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 加载对话列表
const loadConversations = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取数据
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 更新分页信息
    pagination.total = conversationList.value.length
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.conversation-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-title {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.conversation-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.participants {
  display: flex;
  gap: 4px;
}

.participant-avatar {
  flex-shrink: 0;
}

.last-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-preview {
  font-size: 13px;
  color: var(--el-text-color-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.message-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}

@media (max-width: 1200px) {
  .toolbar {
    flex-direction: column;
    gap: 16px;
  }
  
  .toolbar-left {
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 8px;
  }
}
</style>