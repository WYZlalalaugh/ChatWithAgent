<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仪表盘</h1>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stats-card">
        <div class="stats-card-header">
          <span class="stats-card-title">活跃机器人</span>
          <el-icon class="stats-card-icon" style="color: #409EFF;">
            <Robot />
          </el-icon>
        </div>
        <div class="stats-card-value">{{ stats.activeBots }}</div>
        <div class="stats-card-change positive">
          <el-icon><TrendCharts /></el-icon>
          +12% 较昨日
        </div>
      </div>

      <div class="stats-card">
        <div class="stats-card-header">
          <span class="stats-card-title">今日消息</span>
          <el-icon class="stats-card-icon" style="color: #67C23A;">
            <ChatLineRound />
          </el-icon>
        </div>
        <div class="stats-card-value">{{ stats.todayMessages.toLocaleString() }}</div>
        <div class="stats-card-change positive">
          <el-icon><TrendCharts /></el-icon>
          +8% 较昨日
        </div>
      </div>

      <div class="stats-card">
        <div class="stats-card-header">
          <span class="stats-card-title">在线用户</span>
          <el-icon class="stats-card-icon" style="color: #E6A23C;">
            <User />
          </el-icon>
        </div>
        <div class="stats-card-value">{{ stats.onlineUsers }}</div>
        <div class="stats-card-change negative">
          <el-icon><TrendCharts /></el-icon>
          -2% 较昨日
        </div>
      </div>

      <div class="stats-card">
        <div class="stats-card-header">
          <span class="stats-card-title">知识库文档</span>
          <el-icon class="stats-card-icon" style="color: #F56C6C;">
            <Collection />
          </el-icon>
        </div>
        <div class="stats-card-value">{{ stats.knowledgeDocs.toLocaleString() }}</div>
        <div class="stats-card-change positive">
          <el-icon><TrendCharts /></el-icon>
          +25% 较昨日
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px;">
      <!-- 消息趋势图 -->
      <div class="content-card">
        <div style="padding: 20px 20px 0;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3>消息趋势</h3>
            <el-radio-group v-model="messagesTrendPeriod" size="small">
              <el-radio-button label="7d">近7天</el-radio-button>
              <el-radio-button label="30d">近30天</el-radio-button>
              <el-radio-button label="90d">近90天</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div style="height: 300px; padding: 0 20px 20px;">
          <v-chart :option="messagesTrendOption" style="height: 100%;" />
        </div>
      </div>

      <!-- 机器人状态 -->
      <div class="content-card">
        <div style="padding: 20px;">
          <h3 style="margin-bottom: 20px;">机器人状态</h3>
          <div class="bot-status-list">
            <div 
              v-for="bot in botStatus" 
              :key="bot.id" 
              class="bot-status-item"
            >
              <div class="bot-info">
                <div class="bot-name">{{ bot.name }}</div>
                <div class="bot-platform">{{ bot.platform }}</div>
              </div>
              <div class="bot-status">
                <span :class="['status-dot', bot.status]"></span>
                {{ bot.status === 'online' ? '在线' : '离线' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近活动 -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
      <!-- 最近对话 -->
      <div class="content-card">
        <div style="padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3>最近对话</h3>
            <el-button text @click="$router.push('/conversations')">查看全部</el-button>
          </div>
          
          <div class="activity-list">
            <div 
              v-for="conversation in recentConversations" 
              :key="conversation.id"
              class="activity-item"
            >
              <div class="activity-avatar">
                <el-avatar :size="40">
                  {{ conversation.user.charAt(0).toUpperCase() }}
                </el-avatar>
              </div>
              <div class="activity-content">
                <div class="activity-title">{{ conversation.title }}</div>
                <div class="activity-desc">{{ conversation.lastMessage }}</div>
                <div class="activity-time">{{ formatTime(conversation.updatedAt) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统日志 -->
      <div class="content-card">
        <div style="padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3>系统日志</h3>
            <el-button text @click="$router.push('/system/logs')">查看全部</el-button>
          </div>
          
          <div class="activity-list">
            <div 
              v-for="log in systemLogs" 
              :key="log.id"
              class="activity-item"
            >
              <div class="activity-avatar">
                <el-icon :style="`color: ${getLogLevelColor(log.level)}`">
                  <component :is="getLogLevelIcon(log.level)" />
                </el-icon>
              </div>
              <div class="activity-content">
                <div class="activity-title">{{ log.message }}</div>
                <div class="activity-desc">{{ log.source }}</div>
                <div class="activity-time">{{ formatTime(log.timestamp) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import dayjs from 'dayjs'
import {
  Refresh,
  Robot,
  ChatLineRound,
  User,
  Collection,
  TrendCharts,
  InfoFilled,
  WarningFilled,
  CircleCheckFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'

// 注册ECharts组件
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

// 统计数据
const stats = ref({
  activeBots: 12,
  todayMessages: 2847,
  onlineUsers: 156,
  knowledgeDocs: 1204
})

// 消息趋势周期
const messagesTrendPeriod = ref('7d')

// 消息趋势图配置
const messagesTrendOption = ref({
  tooltip: {
    trigger: 'axis'
  },
  legend: {
    data: ['用户消息', '机器人回复']
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: ['01-04', '01-05', '01-06', '01-07', '01-08', '01-09', '01-10']
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '用户消息',
      type: 'line',
      stack: 'Total',
      data: [120, 132, 101, 134, 90, 230, 210],
      smooth: true,
      lineStyle: {
        color: '#409EFF'
      },
      areaStyle: {
        color: 'rgba(64, 158, 255, 0.1)'
      }
    },
    {
      name: '机器人回复',
      type: 'line',
      stack: 'Total',
      data: [220, 182, 191, 234, 290, 330, 310],
      smooth: true,
      lineStyle: {
        color: '#67C23A'
      },
      areaStyle: {
        color: 'rgba(103, 194, 58, 0.1)'
      }
    }
  ]
})

// 机器人状态
const botStatus = ref([
  { id: '1', name: '客服助手', platform: 'QQ', status: 'online' },
  { id: '2', name: '技术支持', platform: '微信', status: 'online' },
  { id: '3', name: '销售顾问', platform: '飞书', status: 'offline' },
  { id: '4', name: '产品介绍', platform: '钉钉', status: 'online' },
  { id: '5', name: '投诉处理', platform: 'QQ', status: 'offline' }
])

// 最近对话
const recentConversations = ref([
  {
    id: '1',
    title: '产品咨询',
    user: '张三',
    lastMessage: '我想了解一下你们的产品功能...',
    updatedAt: '2024-01-10T14:30:00Z'
  },
  {
    id: '2',
    title: '技术支持',
    user: '李四',
    lastMessage: '遇到了一个bug，能帮我看看吗？',
    updatedAt: '2024-01-10T13:45:00Z'
  },
  {
    id: '3',
    title: '价格咨询',
    user: '王五',
    lastMessage: '企业版的价格是多少？',
    updatedAt: '2024-01-10T12:20:00Z'
  }
])

// 系统日志
const systemLogs = ref([
  {
    id: '1',
    level: 'info',
    message: '机器人"客服助手"已成功启动',
    source: '机器人管理',
    timestamp: '2024-01-10T14:30:00Z'
  },
  {
    id: '2',
    level: 'warning',
    message: '知识库存储空间使用率达到80%',
    source: '知识库管理',
    timestamp: '2024-01-10T13:45:00Z'
  },
  {
    id: '3',
    level: 'error',
    message: 'OpenAI API调用失败',
    source: 'LLM服务',
    timestamp: '2024-01-10T12:20:00Z'
  },
  {
    id: '4',
    level: 'success',
    message: '数据库备份完成',
    source: '系统管理',
    timestamp: '2024-01-10T11:00:00Z'
  }
])

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('MM-DD HH:mm')
}

// 获取日志级别颜色
const getLogLevelColor = (level: string) => {
  const colors = {
    info: '#409EFF',
    warning: '#E6A23C',
    error: '#F56C6C',
    success: '#67C23A'
  }
  return colors[level] || '#909399'
}

// 获取日志级别图标
const getLogLevelIcon = (level: string) => {
  const icons = {
    info: InfoFilled,
    warning: WarningFilled,
    error: CircleCloseFilled,
    success: CircleCheckFilled
  }
  return icons[level] || InfoFilled
}

// 刷新数据
const refreshData = () => {
  // TODO: 实际项目中这里应该调用API刷新数据
  console.log('刷新数据')
}

onMounted(() => {
  // 组件挂载时获取数据
  // TODO: 调用API获取实际数据
})
</script>

<style scoped>
.bot-status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bot-status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
}

.bot-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bot-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.bot-platform {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.bot-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  transition: background-color 0.3s;
}

.activity-item:hover {
  background: var(--el-fill-color-lighter);
}

.activity-avatar {
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.activity-title {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.activity-desc {
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-time {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

@media (max-width: 1200px) {
  .page-container {
    padding: 16px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  div[style*="grid-template-columns: 2fr 1fr"] {
    grid-template-columns: 1fr !important;
  }
  
  div[style*="grid-template-columns: 1fr 1fr"] {
    grid-template-columns: 1fr !important;
  }
}
</style>