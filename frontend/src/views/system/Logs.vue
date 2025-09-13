<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统日志</h1>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="fetchLogs">刷新</el-button>
        <el-button :icon="Delete" @click="clearLogs" type="danger">清空日志</el-button>
      </div>
    </div>

    <el-card>
      <!-- 筛选工具栏 -->
      <template #header>
        <div class="log-filters">
          <el-select
            v-model="logLevel"
            placeholder="日志级别"
            clearable
            style="width: 120px;"
            @change="fetchLogs"
          >
            <el-option label="DEBUG" value="debug" />
            <el-option label="INFO" value="info" />
            <el-option label="WARNING" value="warning" />
            <el-option label="ERROR" value="error" />
            <el-option label="CRITICAL" value="critical" />
          </el-select>
          
          <el-input
            v-model="searchText"
            placeholder="搜索日志内容..."
            style="width: 300px;"
            @input="handleSearch"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            @change="fetchLogs"
          />
        </div>
      </template>

      <el-table
        :data="logs"
        v-loading="loading"
        height="600"
        stripe
        :row-class-name="getRowClassName"
      >
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag
              :type="getLogLevelType(row.level)"
              effect="plain"
            >
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="module" label="模块" width="150" />
        
        <el-table-column prop="message" label="消息" show-overflow-tooltip min-width="300">
          <template #default="{ row }">
            <div class="log-message" @click="showLogDetail(row)">
              {{ row.message }}
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="user_id" label="用户ID" width="100" />
        
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="showLogDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchLogs"
        @current-change="fetchLogs"
        style="margin-top: 20px; text-align: center;"
      />
    </el-card>

    <!-- 日志详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="日志详情"
      width="70%"
      :before-close="handleDetailClose"
    >
      <div v-if="selectedLog" class="log-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="时间">
            {{ formatTime(selectedLog.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="级别">
            <el-tag :type="getLogLevelType(selectedLog.level)">
              {{ selectedLog.level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="模块">
            {{ selectedLog.module }}
          </el-descriptions-item>
          <el-descriptions-item label="用户ID">
            {{ selectedLog.user_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="请求ID">
            {{ selectedLog.request_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">
            {{ selectedLog.ip_address || '-' }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="log-content">
          <h4>消息内容:</h4>
          <pre class="log-message-detail">{{ selectedLog.message }}</pre>
        </div>
        
        <div v-if="selectedLog.stack_trace" class="log-stack">
          <h4>堆栈跟踪:</h4>
          <pre class="stack-trace">{{ selectedLog.stack_trace }}</pre>
        </div>
        
        <div v-if="selectedLog.context" class="log-context">
          <h4>上下文信息:</h4>
          <pre class="context-info">{{ JSON.stringify(selectedLog.context, null, 2) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete, Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const logLevel = ref('')
const searchText = ref('')
const dateRange = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const detailDialogVisible = ref(false)
const selectedLog = ref<any>(null)

// 模拟日志数据
const logs = ref([
  {
    id: '1',
    timestamp: '2024-01-10T14:30:25.123Z',
    level: 'INFO',
    module: 'auth',
    message: '用户登录成功',
    user_id: 'user_123',
    request_id: 'req_456',
    ip_address: '192.168.1.100'
  },
  {
    id: '2',
    timestamp: '2024-01-10T14:28:15.456Z',
    level: 'ERROR',
    module: 'api',
    message: '数据库连接失败: Connection timeout',
    user_id: null,
    request_id: 'req_789',
    ip_address: '192.168.1.101',
    stack_trace: 'SQLAlchemyError: Connection timeout\n  at Database.connect()\n  at ...'
  },
  {
    id: '3',
    timestamp: '2024-01-10T14:25:30.789Z',
    level: 'WARNING',
    module: 'bot',
    message: '机器人响应时间超过阈值: 5.2s',
    user_id: 'user_456',
    request_id: 'req_012',
    ip_address: '192.168.1.102',
    context: {
      bot_id: 'bot_123',
      response_time: 5.2,
      threshold: 3.0
    }
  }
])

// 获取日志级别对应的标签类型
const getLogLevelType = (level: string): string => {
  const types: Record<string, string> = {
    'DEBUG': 'info',
    'INFO': 'success',
    'WARNING': 'warning',
    'ERROR': 'danger',
    'CRITICAL': 'danger'
  }
  return types[level] || 'info'
}

// 获取表格行的类名
const getRowClassName = ({ row }: { row: any }) => {
  if (row.level === 'ERROR' || row.level === 'CRITICAL') {
    return 'error-row'
  } else if (row.level === 'WARNING') {
    return 'warning-row'
  }
  return ''
}

// 格式化时间
const formatTime = (timestamp: string) => {
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss.SSS')
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  fetchLogs()
}

// 显示日志详情
const showLogDetail = (log: any) => {
  selectedLog.value = log
  detailDialogVisible.value = true
}

// 关闭详情对话框
const handleDetailClose = () => {
  detailDialogVisible.value = false
  selectedLog.value = null
}

// 获取日志列表
const fetchLogs = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取日志数据
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟数据过滤
    let filteredLogs = [...logs.value]
    
    if (logLevel.value) {
      filteredLogs = filteredLogs.filter(log => log.level === logLevel.value.toUpperCase())
    }
    
    if (searchText.value) {
      filteredLogs = filteredLogs.filter(log => 
        log.message.toLowerCase().includes(searchText.value.toLowerCase())
      )
    }
    
    total.value = filteredLogs.length
    
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

// 清空日志
const clearLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有日志吗？此操作不可恢复。', '警告', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    
    // TODO: 调用API清空日志
    logs.value = []
    total.value = 0
    ElMessage.success('日志已清空')
    
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.log-filters {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.log-message {
  cursor: pointer;
  transition: color 0.2s;
}

.log-message:hover {
  color: var(--el-color-primary);
}

.log-detail {
  padding: 16px 0;
}

.log-content,
.log-stack,
.log-context {
  margin-top: 20px;
}

.log-content h4,
.log-stack h4,
.log-context h4 {
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

.log-message-detail,
.stack-trace,
.context-info {
  background: var(--el-bg-color-page);
  padding: 12px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.stack-trace {
  color: var(--el-color-danger);
}

:deep(.error-row) {
  background-color: rgba(245, 108, 108, 0.1) !important;
}

:deep(.warning-row) {
  background-color: rgba(230, 162, 60, 0.1) !important;
}

@media (max-width: 768px) {
  .log-filters {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .log-filters .el-select,
  .log-filters .el-input {
    width: 100% !important;
  }
}
</style>