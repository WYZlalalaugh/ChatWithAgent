<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">机器人详情</h1>
      <div class="page-actions">
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="editBot">编辑机器人</el-button>
      </div>
    </div>

    <div v-loading="loading" class="bot-detail">
      <!-- 基本信息卡片 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-tag :type="botInfo?.is_active ? 'success' : 'info'">
              {{ botInfo?.is_active ? '已启用' : '已禁用' }}
            </el-tag>
          </div>
        </template>
        
        <div class="bot-basic-info">
          <div class="bot-avatar-section">
            <el-avatar :src="botInfo?.avatar_url" :size="80">
              {{ botInfo?.name?.charAt(0) }}
            </el-avatar>
          </div>
          
          <div class="bot-info-section">
            <div class="info-item">
              <label>机器人名称：</label>
              <span>{{ botInfo?.name }}</span>
            </div>
            
            <div class="info-item">
              <label>描述：</label>
              <span>{{ botInfo?.description || '暂无描述' }}</span>
            </div>
            
            <div class="info-item">
              <label>平台类型：</label>
              <el-tag :type="getPlatformTagType(botInfo?.platform_type)">
                {{ getPlatformName(botInfo?.platform_type) }}
              </el-tag>
            </div>
            
            <div class="info-item">
              <label>创建时间：</label>
              <span>{{ formatTime(botInfo?.created_at) }}</span>
            </div>
            
            <div class="info-item">
              <label>最后更新：</label>
              <span>{{ formatTime(botInfo?.updated_at) }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 运行状态卡片 -->
      <el-card class="status-card">
        <template #header>
          <div class="card-header">
            <span>运行状态</span>
            <el-button 
              :type="botInfo?.is_online ? 'warning' : 'success'"
              size="small"
              @click="toggleBotStatus"
            >
              {{ botInfo?.is_online ? '停止' : '启动' }}
            </el-button>
          </div>
        </template>
        
        <div class="status-grid">
          <div class="status-item">
            <div class="status-label">在线状态</div>
            <div class="status-value">
              <el-tag :type="botInfo?.is_online ? 'success' : 'info'">
                {{ botInfo?.is_online ? '在线' : '离线' }}
              </el-tag>
            </div>
          </div>
          
          <div class="status-item">
            <div class="status-label">消息总数</div>
            <div class="status-value">{{ botInfo?.message_count || 0 }}</div>
          </div>
          
          <div class="status-item">
            <div class="status-label">最后活动</div>
            <div class="status-value">
              {{ botInfo?.last_active ? formatTime(botInfo.last_active) : '从未活动' }}
            </div>
          </div>
          
          <div class="status-item">
            <div class="status-label">今日消息</div>
            <div class="status-value">{{ todayMessages }}</div>
          </div>
        </div>
      </el-card>

      <!-- AI 配置卡片 -->
      <el-card class="config-card">
        <template #header>
          <span>AI 配置</span>
        </template>
        
        <div class="config-info">
          <div class="config-item">
            <label>模型提供商：</label>
            <span>{{ botInfo?.llm_config?.provider }}</span>
          </div>
          
          <div class="config-item">
            <label>模型：</label>
            <span>{{ botInfo?.llm_config?.model }}</span>
          </div>
          
          <div class="config-item">
            <label>温度：</label>
            <span>{{ botInfo?.llm_config?.temperature }}</span>
          </div>
          
          <div class="config-item">
            <label>最大令牌数：</label>
            <span>{{ botInfo?.llm_config?.max_tokens }}</span>
          </div>
          
          <div class="config-item full-width">
            <label>系统提示词：</label>
            <div class="system-prompt">
              {{ botInfo?.llm_config?.system_prompt || '暂无设置' }}
            </div>
          </div>
        </div>
      </el-card>

      <!-- 最近对话卡片 -->
      <el-card class="conversations-card">
        <template #header>
          <div class="card-header">
            <span>最近对话</span>
            <el-button type="primary" size="small" @click="viewAllConversations">
              查看全部
            </el-button>
          </div>
        </template>
        
        <el-table :data="recentConversations" stripe>
          <el-table-column prop="title" label="对话标题" />
          <el-table-column prop="message_count" label="消息数" width="100" />
          <el-table-column prop="last_message_at" label="最后消息" width="150">
            <template #default="{ row }">
              {{ formatTime(row.last_message_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="viewConversation(row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div v-if="recentConversations.length === 0" class="empty-data">
          暂无对话记录
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

// 数据状态
const loading = ref(false)
const botInfo = ref<any>(null)
const recentConversations = ref([])

// 机器人ID
const botId = route.params.id as string

// 计算属性
const todayMessages = computed(() => {
  // TODO: 实际计算今日消息数
  return 42
})

// 获取平台标签类型
const getPlatformTagType = (platform: string) => {
  const types = {
    qq: 'primary',
    wechat: 'success',
    feishu: 'warning',
    dingtalk: 'info',
    telegram: 'danger'
  }
  return types[platform] || 'info'
}

// 获取平台名称
const getPlatformName = (platform: string) => {
  const names = {
    qq: 'QQ',
    wechat: '微信',
    feishu: '飞书',
    dingtalk: '钉钉',
    telegram: 'Telegram'
  }
  return names[platform] || platform
}

// 格式化时间
const formatTime = (time: string) => {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 编辑机器人
const editBot = () => {
  router.push(`/bots/${botId}/edit`)
}

// 切换机器人状态
const toggleBotStatus = async () => {
  try {
    const action = botInfo.value?.is_online ? '停止' : '启动'
    await ElMessageBox.confirm(`确定要${action}机器人"${botInfo.value?.name}"吗？`, '确认')
    
    // TODO: 调用API切换状态
    if (botInfo.value) {
      botInfo.value.is_online = !botInfo.value.is_online
    }
    ElMessage.success(`${action}成功`)
  } catch {
    // 用户取消
  }
}

// 查看所有对话
const viewAllConversations = () => {
  router.push(`/conversations?bot_id=${botId}`)
}

// 查看对话详情
const viewConversation = (conversation: any) => {
  router.push(`/conversations/${conversation.id}/detail`)
}

// 加载机器人详情
const loadBotInfo = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取机器人详情
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟数据
    botInfo.value = {
      id: botId,
      name: '客服助手',
      description: '7x24小时在线客服，处理用户咨询',
      avatar_url: '',
      platform_type: 'qq',
      is_active: true,
      is_online: true,
      message_count: 1245,
      last_active: '2024-01-10T14:30:00Z',
      created_at: '2024-01-05T10:00:00Z',
      updated_at: '2024-01-10T14:30:00Z',
      llm_config: {
        provider: 'OpenAI',
        model: 'gpt-3.5-turbo',
        temperature: 0.7,
        max_tokens: 2000,
        system_prompt: '你是一个专业的客服助手，请用友好、耐心的语气帮助用户解决问题。'
      }
    }
    
    // 模拟最近对话数据
    recentConversations.value = [
      {
        id: '1',
        title: '用户咨询产品功能',
        message_count: 12,
        last_message_at: '2024-01-10T14:30:00Z'
      },
      {
        id: '2',
        title: '技术支持请求',
        message_count: 8,
        last_message_at: '2024-01-10T13:15:00Z'
      }
    ]
  } catch (error) {
    ElMessage.error('加载机器人详情失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBotInfo()
})
</script>

<style scoped>
.bot-detail {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-card .bot-basic-info {
  display: flex;
  gap: 24px;
}

.bot-avatar-section {
  flex-shrink: 0;
}

.bot-info-section {
  flex: 1;
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

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.status-item {
  text-align: center;
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.status-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.status-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.config-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.config-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.config-item.full-width {
  grid-column: 1 / -1;
  flex-direction: column;
  align-items: flex-start;
}

.config-item label {
  font-weight: 500;
  color: var(--el-text-color-secondary);
  min-width: 100px;
}

.system-prompt {
  background: var(--el-bg-color-page);
  padding: 12px;
  border-radius: 6px;
  line-height: 1.6;
  width: 100%;
  max-height: 120px;
  overflow-y: auto;
}

.empty-data {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 40px 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .bot-basic-info {
    flex-direction: column;
    text-align: center;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .config-info {
    grid-template-columns: 1fr;
  }
}
</style>