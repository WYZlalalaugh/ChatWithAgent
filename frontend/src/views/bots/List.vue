<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">机器人管理</h1>
      <div class="page-actions">
        <el-button type="primary" :icon="Plus" @click="createBot">
          创建机器人
        </el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索机器人名称..."
          :prefix-icon="Search"
          clearable
          style="width: 300px;"
          @input="handleSearch"
        />
        <el-select
          v-model="platformFilter"
          placeholder="平台类型"
          clearable
          style="width: 150px;"
          @change="handleSearch"
        >
          <el-option label="QQ" value="qq" />
          <el-option label="微信" value="wechat" />
          <el-option label="飞书" value="feishu" />
          <el-option label="钉钉" value="dingtalk" />
          <el-option label="Telegram" value="telegram" />
        </el-select>
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 120px;"
          @change="handleSearch"
        >
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="已停用" value="disabled" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
        <el-dropdown @command="handleBatchAction">
          <el-button>
            批量操作
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="start" :disabled="!hasSelection">
                批量启动
              </el-dropdown-item>
              <el-dropdown-item command="stop" :disabled="!hasSelection">
                批量停止
              </el-dropdown-item>
              <el-dropdown-item command="delete" :disabled="!hasSelection" divided>
                批量删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 机器人列表 -->
    <div class="content-card">
      <el-table
        v-loading="loading"
        :data="botList"
        @selection-change="handleSelectionChange"
        stripe
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column label="机器人信息" min-width="200">
          <template #default="{ row }">
            <div class="bot-info">
              <el-avatar
                :src="row.avatar_url"
                :size="40"
                class="bot-avatar"
              >
                {{ row.name.charAt(0).toUpperCase() }}
              </el-avatar>
              <div class="bot-details">
                <div class="bot-name">{{ row.name }}</div>
                <div class="bot-description">{{ row.description || '暂无描述' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="平台" width="100">
          <template #default="{ row }">
            <el-tag :type="getPlatformTagType(row.platform_type)">
              {{ getPlatformName(row.platform_type) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <div class="status-column">
              <span :class="['status-dot', getStatusClass(row)]"></span>
              {{ getStatusText(row) }}
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="消息统计" width="120">
          <template #default="{ row }">
            <div class="stats-column">
              <div class="stat-item">
                <span class="stat-value">{{ row.message_count || 0 }}</span>
                <span class="stat-label">消息</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="最后活动" width="120">
          <template #default="{ row }">
            {{ row.last_active ? formatTime(row.last_active) : '从未活动' }}
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="120">
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
                  @click="viewBot(row)"
                />
              </el-tooltip>
              
              <el-tooltip content="编辑">
                <el-button
                  text
                  :icon="Edit"
                  @click="editBot(row)"
                />
              </el-tooltip>
              
              <el-tooltip :content="row.is_active ? '停止' : '启动'">
                <el-button
                  text
                  :icon="row.is_active ? VideoPause : VideoPlay"
                  :type="row.is_active ? 'warning' : 'success'"
                  @click="toggleBot(row)"
                />
              </el-tooltip>
              
              <el-tooltip content="配置">
                <el-button
                  text
                  :icon="Setting"
                  @click="configBot(row)"
                />
              </el-tooltip>
              
              <el-popconfirm
                title="确定要删除这个机器人吗？"
                @confirm="deleteBot(row)"
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Search,
  Refresh,
  ArrowDown,
  View,
  Edit,
  VideoPlay,
  VideoPause,
  Setting,
  Delete
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()

// 数据状态
const loading = ref(false)
const searchQuery = ref('')
const platformFilter = ref('')
const statusFilter = ref('')
const selectedBots = ref([])

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 机器人列表数据（模拟数据）
const botList = ref([
  {
    id: '1',
    name: '客服助手',
    description: '7x24小时在线客服，处理用户咨询',
    avatar_url: '',
    platform_type: 'qq',
    is_active: true,
    is_online: true,
    message_count: 1245,
    last_active: '2024-01-10T14:30:00Z',
    created_at: '2024-01-05T10:00:00Z'
  },
  {
    id: '2',
    name: '技术支持',
    description: '专业技术问题解答',
    avatar_url: '',
    platform_type: 'wechat',
    is_active: true,
    is_online: false,
    message_count: 892,
    last_active: '2024-01-10T12:15:00Z',
    created_at: '2024-01-03T09:30:00Z'
  },
  {
    id: '3',
    name: '销售顾问',
    description: '产品介绍和销售支持',
    avatar_url: '',
    platform_type: 'feishu',
    is_active: false,
    is_online: false,
    message_count: 567,
    last_active: '2024-01-09T16:45:00Z',
    created_at: '2024-01-01T14:20:00Z'
  }
])

// 计算属性
const hasSelection = computed(() => selectedBots.value.length > 0)

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

// 获取状态样式类
const getStatusClass = (bot: any) => {
  if (!bot.is_active) return 'offline'
  return bot.is_online ? 'online' : 'offline'
}

// 获取状态文本
const getStatusText = (bot: any) => {
  if (!bot.is_active) return '已停用'
  return bot.is_online ? '在线' : '离线'
}

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('MM-DD HH:mm')
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  loadBots()
}

// 刷新数据
const refreshData = () => {
  loadBots()
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedBots.value = selection
}

// 批量操作
const handleBatchAction = (command: string) => {
  if (selectedBots.value.length === 0) {
    ElMessage.warning('请先选择要操作的机器人')
    return
  }
  
  switch (command) {
    case 'start':
      batchStart()
      break
    case 'stop':
      batchStop()
      break
    case 'delete':
      batchDelete()
      break
  }
}

// 批量启动
const batchStart = async () => {
  try {
    await ElMessageBox.confirm(`确定要启动选中的 ${selectedBots.value.length} 个机器人吗？`, '确认')
    // TODO: 调用API批量启动
    ElMessage.success('批量启动成功')
    loadBots()
  } catch {
    // 用户取消
  }
}

// 批量停止
const batchStop = async () => {
  try {
    await ElMessageBox.confirm(`确定要停止选中的 ${selectedBots.value.length} 个机器人吗？`, '确认')
    // TODO: 调用API批量停止
    ElMessage.success('批量停止成功')
    loadBots()
  } catch {
    // 用户取消
  }
}

// 批量删除
const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedBots.value.length} 个机器人吗？此操作不可恢复。`,
      '警告',
      { type: 'warning' }
    )
    // TODO: 调用API批量删除
    ElMessage.success('批量删除成功')
    loadBots()
  } catch {
    // 用户取消
  }
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  loadBots()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadBots()
}

// 创建机器人
const createBot = () => {
  router.push('/bots/create')
}

// 查看详情
const viewBot = (bot: any) => {
  router.push(`/bots/${bot.id}/detail`)
}

// 编辑机器人
const editBot = (bot: any) => {
  router.push(`/bots/${bot.id}/edit`)
}

// 切换机器人状态
const toggleBot = async (bot: any) => {
  try {
    const action = bot.is_active ? '停止' : '启动'
    await ElMessageBox.confirm(`确定要${action}机器人"${bot.name}"吗？`, '确认')
    
    // TODO: 调用API切换状态
    bot.is_active = !bot.is_active
    ElMessage.success(`${action}成功`)
  } catch {
    // 用户取消
  }
}

// 配置机器人
const configBot = (bot: any) => {
  router.push(`/bots/${bot.id}/edit?tab=config`)
}

// 删除机器人
const deleteBot = async (bot: any) => {
  try {
    // TODO: 调用API删除
    ElMessage.success('删除成功')
    loadBots()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 加载机器人列表
const loadBots = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取数据
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 更新分页信息
    pagination.total = botList.value.length
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBots()
})
</script>

<style scoped>
.bot-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bot-avatar {
  flex-shrink: 0;
}

.bot-details {
  flex: 1;
  min-width: 0;
}

.bot-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.bot-description {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-column {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.stats-column {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.stat-label {
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