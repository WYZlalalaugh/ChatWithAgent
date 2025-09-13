<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统监控</h1>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          @change="toggleAutoRefresh"
        />
      </div>
    </div>

    <!-- 系统状态概览 -->
    <div class="stats-grid">
      <el-card class="stat-card">
        <div class="stat-header">
          <el-icon class="stat-icon" color="#67c23a"><Monitor /></el-icon>
          <span>系统状态</span>
        </div>
        <div class="stat-value">
          <el-tag :type="systemStatus === 'healthy' ? 'success' : 'danger'">
            {{ systemStatus === 'healthy' ? '正常' : '异常' }}
          </el-tag>
        </div>
      </el-card>

      <el-card class="stat-card">
        <div class="stat-header">
          <el-icon class="stat-icon" color="#409eff"><Cpu /></el-icon>
          <span>CPU 使用率</span>
        </div>
        <div class="stat-value">{{ cpuUsage }}%</div>
        <el-progress
          :percentage="cpuUsage"
          :color="getProgressColor(cpuUsage)"
          :show-text="false"
        />
      </el-card>

      <el-card class="stat-card">
        <div class="stat-header">
          <el-icon class="stat-icon" color="#e6a23c"><Memo /></el-icon>
          <span>内存使用率</span>
        </div>
        <div class="stat-value">{{ memoryUsage }}%</div>
        <el-progress
          :percentage="memoryUsage"
          :color="getProgressColor(memoryUsage)"
          :show-text="false"
        />
      </el-card>

      <el-card class="stat-card">
        <div class="stat-header">
          <el-icon class="stat-icon" color="#f56c6c"><Timer /></el-icon>
          <span>运行时间</span>
        </div>
        <div class="stat-value">{{ uptime }}</div>
      </el-card>
    </div>

    <!-- 图表区域 -->
    <el-row :gutter="24">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>CPU 使用率趋势</span>
          </template>
          <div ref="cpuChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>内存使用率趋势</span>
          </template>
          <div ref="memoryChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 服务状态 -->
    <el-row :gutter="24" style="margin-top: 24px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>服务状态</span>
          </template>
          <el-table :data="services" style="width: 100%">
            <el-table-column prop="name" label="服务名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'running' ? 'success' : 'danger'">
                  {{ row.status === 'running' ? '运行中' : '已停止' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="port" label="端口" width="80" />
            <el-table-column prop="uptime" label="运行时间" width="120" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span>API 接口统计</span>
          </template>
          <el-table :data="apiStats" stripe>
            <el-table-column prop="endpoint" label="接口" width="200" />
            <el-table-column prop="method" label="方法" width="100">
              <template #default="{ row }">
                <el-tag :type="getMethodType(row.method)">
                  {{ row.method }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="请求次数" width="120" />
            <el-table-column prop="avg_time" label="平均响应时间(ms)" width="150" />
            <el-table-column prop="success_rate" label="成功率" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.success_rate"
                  :color="row.success_rate > 95 ? '#67c23a' : row.success_rate > 90 ? '#e6a23c' : '#f56c6c'"
                />
              </template>
            </el-table-column>
            <el-table-column prop="last_request" label="最后请求时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Refresh, Monitor, Cpu, Memo, Timer } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const cpuChartRef = ref()
const memoryChartRef = ref()
let refreshTimer: any = null
let cpuChart: any = null
let memoryChart: any = null

// 响应式数据
const autoRefresh = ref(true)
const systemStatus = ref('healthy')
const cpuUsage = ref(35)
const memoryUsage = ref(68)
const uptime = ref('3天 12小时 45分钟')

// 服务状态数据
const services = ref([
  {
    name: 'Web Server',
    status: 'running',
    port: 3001,
    uptime: '3天 12小时'
  },
  {
    name: 'API Server',
    status: 'running',
    port: 9800,
    uptime: '3天 12小时'
  },
  {
    name: 'Database',
    status: 'running',
    port: 5432,
    uptime: '3天 12小时'
  },
  {
    name: 'Redis',
    status: 'running',
    port: 6379,
    uptime: '3天 12小时'
  }
])

// API 统计数据
const apiStats = ref([
  {
    endpoint: '/api/v1/auth/login',
    method: 'POST',
    count: 1245,
    avg_time: 125,
    success_rate: 98.5,
    last_request: '2分钟前'
  },
  {
    endpoint: '/api/v1/bots',
    method: 'GET',
    count: 3456,
    avg_time: 89,
    success_rate: 99.2,
    last_request: '1分钟前'
  },
  {
    endpoint: '/api/v1/chat',
    method: 'POST',
    count: 8923,
    avg_time: 234,
    success_rate: 97.8,
    last_request: '30秒前'
  }
])

// 获取进度条颜色
const getProgressColor = (percentage: number) => {
  if (percentage < 50) return '#67c23a'
  if (percentage < 80) return '#e6a23c'
  return '#f56c6c'
}

// 获取HTTP方法对应的标签类型
const getMethodType = (method: string): string => {
  const types: Record<string, string> = {
    'GET': 'success',
    'POST': 'primary',
    'PUT': 'warning',
    'DELETE': 'danger',
    'PATCH': 'info'
  }
  return types[method] || 'info'
}

// 初始化CPU图表
const initCpuChart = () => {
  if (!cpuChartRef.value) return
  
  cpuChart = echarts.init(cpuChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: generateTimeLabels()
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [{
      name: 'CPU使用率',
      type: 'line',
      smooth: true,
      data: generateCpuData(),
      itemStyle: {
        color: '#409eff'
      },
      areaStyle: {
        opacity: 0.3
      }
    }]
  }
  
  cpuChart.setOption(option)
}

// 初始化内存图表
const initMemoryChart = () => {
  if (!memoryChartRef.value) return
  
  memoryChart = echarts.init(memoryChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: generateTimeLabels()
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [{
      name: '内存使用率',
      type: 'line',
      smooth: true,
      data: generateMemoryData(),
      itemStyle: {
        color: '#e6a23c'
      },
      areaStyle: {
        opacity: 0.3
      }
    }]
  }
  
  memoryChart.setOption(option)
}

// 生成时间标签
const generateTimeLabels = () => {
  const labels = []
  const now = new Date()
  for (let i = 29; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 60000)
    labels.push(time.toTimeString().slice(0, 5))
  }
  return labels
}

// 生成CPU数据
const generateCpuData = () => {
  const data = []
  for (let i = 0; i < 30; i++) {
    data.push(Math.floor(Math.random() * 40) + 20)
  }
  return data
}

// 生成内存数据
const generateMemoryData = () => {
  const data = []
  for (let i = 0; i < 30; i++) {
    data.push(Math.floor(Math.random() * 30) + 50)
  }
  return data
}

// 刷新数据
const refreshData = async () => {
  // 模拟数据更新
  cpuUsage.value = Math.floor(Math.random() * 60) + 20
  memoryUsage.value = Math.floor(Math.random() * 40) + 50
  
  // 更新图表数据
  if (cpuChart) {
    cpuChart.setOption({
      series: [{
        data: generateCpuData()
      }]
    })
  }
  
  if (memoryChart) {
    memoryChart.setOption({
      series: [{
        data: generateMemoryData()
      }]
    })
  }
}

// 切换自动刷新
const toggleAutoRefresh = (enabled: boolean) => {
  if (enabled) {
    refreshTimer = setInterval(refreshData, 10000) // 10秒刷新一次
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 生命周期钩子
onMounted(async () => {
  await nextTick()
  initCpuChart()
  initMemoryChart()
  
  if (autoRefresh.value) {
    toggleAutoRefresh(true)
  }
  
  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    cpuChart?.resize()
    memoryChart?.resize()
  })
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  cpuChart?.dispose()
  memoryChart?.dispose()
  
  window.removeEventListener('resize', () => {
    cpuChart?.resize()
    memoryChart?.resize()
  })
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.stat-icon {
  font-size: 20px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>