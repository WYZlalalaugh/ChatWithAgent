<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">已安装插件</h1>
      <div class="page-actions">
        <el-button type="primary" @click="$router.push('/plugins/marketplace')">
          插件市场
        </el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索插件名称..."
          :prefix-icon="Search"
          clearable
          style="width: 300px;"
          @input="handleSearch"
        />
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 120px;"
          @change="handleSearch"
        >
          <el-option label="已启用" value="enabled" />
          <el-option label="已禁用" value="disabled" />
        </el-select>
        <el-select
          v-model="categoryFilter"
          placeholder="分类"
          clearable
          style="width: 150px;"
          @change="handleSearch"
        >
          <el-option label="工具类" value="tool" />
          <el-option label="娱乐类" value="entertainment" />
          <el-option label="信息查询" value="information" />
          <el-option label="数据处理" value="data" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
      </div>
    </div>

    <!-- 插件列表 -->
    <div class="plugins-grid">
      <el-card
        v-for="plugin in pluginList"
        :key="plugin.id"
        class="plugin-card"
        :class="{ 'disabled': plugin.status === 'disabled' }"
      >
        <template #header>
          <div class="plugin-header">
            <div class="plugin-title">
              <el-icon class="plugin-icon" :color="plugin.icon_color">
                <component :is="plugin.icon" />
              </el-icon>
              <span class="plugin-name">{{ plugin.name }}</span>
            </div>
            <el-switch
              v-model="plugin.status"
              active-value="enabled"
              inactive-value="disabled"
              @change="togglePlugin(plugin)"
            />
          </div>
        </template>
        
        <div class="plugin-content">
          <div class="plugin-description">
            {{ plugin.description }}
          </div>
          
          <div class="plugin-meta">
            <el-tag :type="getCategoryTagType(plugin.category)" size="small">
              {{ getCategoryName(plugin.category) }}
            </el-tag>
            <span class="plugin-version">v{{ plugin.version }}</span>
          </div>
          
          <div class="plugin-stats">
            <div class="stat-item">
              <span class="stat-label">调用次数:</span>
              <span class="stat-value">{{ plugin.call_count || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最后使用:</span>
              <span class="stat-value">{{ plugin.last_used ? formatTime(plugin.last_used) : '从未使用' }}</span>
            </div>
          </div>
        </div>
        
        <template #footer>
          <div class="plugin-actions">
            <el-button size="small" @click="configPlugin(plugin)">
              配置
            </el-button>
            <el-button size="small" @click="viewLogs(plugin)">
              日志
            </el-button>
            <el-popconfirm
              title="确定要卸载这个插件吗？"
              @confirm="uninstallPlugin(plugin)"
            >
              <template #reference>
                <el-button size="small" type="danger">
                  卸载
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-card>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredPluginList.length === 0" class="empty-state">
      <el-empty description="暂无已安装的插件">
        <el-button type="primary" @click="$router.push('/plugins/marketplace')">
          去插件市场安装
        </el-button>
      </el-empty>
    </div>

    <!-- 插件配置对话框 -->
    <el-dialog
      v-model="configDialogVisible"
      :title="`配置插件 - ${selectedPlugin?.name}`"
      width="600px"
      :before-close="handleConfigDialogClose"
    >
      <div v-if="selectedPlugin" class="plugin-config">
        <el-form
          ref="configFormRef"
          :model="pluginConfig"
          label-width="120px"
        >
          <el-form-item
            v-for="(setting, key) in selectedPlugin.settings"
            :key="key"
            :label="setting.label"
            :prop="key"
          >
            <el-input
              v-if="setting.type === 'string'"
              v-model="pluginConfig[key]"
              :placeholder="setting.placeholder"
            />
            <el-input-number
              v-else-if="setting.type === 'number'"
              v-model="pluginConfig[key]"
              :min="setting.min"
              :max="setting.max"
            />
            <el-switch
              v-else-if="setting.type === 'boolean'"
              v-model="pluginConfig[key]"
            />
            <el-select
              v-else-if="setting.type === 'select'"
              v-model="pluginConfig[key]"
              :placeholder="setting.placeholder"
            >
              <el-option
                v-for="option in setting.options"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
            <div v-if="setting.description" class="setting-description">
              {{ setting.description }}
            </div>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePluginConfig" :loading="configSaving">
          保存配置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import {
  Search,
  Refresh,
  Setting,
  Document,
  ChatDotRound,
  Coordinate,
  DataAnalysis
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()

// 数据状态
const loading = ref(false)
const configSaving = ref(false)
const configDialogVisible = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const categoryFilter = ref('')
const selectedPlugin = ref<any>(null)

// 表单引用
const configFormRef = ref<FormInstance>()

// 插件配置数据
const pluginConfig = reactive<Record<string, any>>({})

// 插件列表数据（模拟数据）
const pluginList = ref([
  {
    id: '1',
    name: '天气查询',
    description: '查询全球各地的天气信息，支持实时天气和天气预报',
    category: 'information',
    version: '1.2.0',
    status: 'enabled',
    icon: 'Coordinate',
    icon_color: '#409eff',
    call_count: 245,
    last_used: '2024-01-10T14:30:00Z',
    settings: {
      api_key: {
        label: 'API密钥',
        type: 'string',
        placeholder: '请输入天气API密钥',
        description: '从天气服务提供商获取的API密钥'
      },
      default_city: {
        label: '默认城市',
        type: 'string',
        placeholder: '北京',
        description: '当用户未指定城市时使用的默认城市'
      },
      unit: {
        label: '温度单位',
        type: 'select',
        options: [
          { label: '摄氏度', value: 'celsius' },
          { label: '华氏度', value: 'fahrenheit' }
        ],
        description: '显示温度的单位'
      }
    }
  },
  {
    id: '2',
    name: '快递查询',
    description: '查询各大快递公司的物流信息',
    category: 'information',
    version: '1.0.5',
    status: 'enabled',
    icon: 'Document',
    icon_color: '#67c23a',
    call_count: 89,
    last_used: '2024-01-09T16:45:00Z',
    settings: {
      auto_detect: {
        label: '自动识别快递公司',
        type: 'boolean',
        description: '是否自动识别快递公司类型'
      },
      timeout: {
        label: '超时时间(秒)',
        type: 'number',
        min: 5,
        max: 60,
        description: '查询超时时间'
      }
    }
  },
  {
    id: '3',
    name: '翻译助手',
    description: '多语言翻译工具，支持100+种语言互译',
    category: 'tool',
    version: '2.1.0',
    status: 'disabled',
    icon: 'ChatDotRound',
    icon_color: '#e6a23c',
    call_count: 156,
    last_used: '2024-01-08T11:20:00Z',
    settings: {
      provider: {
        label: '翻译服务商',
        type: 'select',
        options: [
          { label: 'Google翻译', value: 'google' },
          { label: '百度翻译', value: 'baidu' },
          { label: '有道翻译', value: 'youdao' }
        ],
        description: '选择翻译服务提供商'
      },
      api_key: {
        label: 'API密钥',
        type: 'string',
        placeholder: '请输入翻译API密钥'
      }
    }
  },
  {
    id: '4',
    name: '数据分析',
    description: '对数据进行统计分析和可视化',
    category: 'data',
    version: '1.5.2',
    status: 'enabled',
    icon: 'DataAnalysis',
    icon_color: '#f56c6c',
    call_count: 45,
    last_used: '2024-01-07T09:15:00Z',
    settings: {
      max_rows: {
        label: '最大处理行数',
        type: 'number',
        min: 100,
        max: 10000,
        description: '单次处理的最大数据行数'
      },
      chart_type: {
        label: '默认图表类型',
        type: 'select',
        options: [
          { label: '柱状图', value: 'bar' },
          { label: '折线图', value: 'line' },
          { label: '饼图', value: 'pie' }
        ]
      }
    }
  }
])

// 计算属性 - 过滤后的插件列表
const filteredPluginList = computed(() => {
  let filtered = [...pluginList.value]
  
  if (searchQuery.value) {
    filtered = filtered.filter(plugin => 
      plugin.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      plugin.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }
  
  if (statusFilter.value) {
    filtered = filtered.filter(plugin => plugin.status === statusFilter.value)
  }
  
  if (categoryFilter.value) {
    filtered = filtered.filter(plugin => plugin.category === categoryFilter.value)
  }
  
  return filtered
})

// 获取分类标签类型
const getCategoryTagType = (category: string) => {
  const types = {
    tool: 'primary',
    entertainment: 'success',
    information: 'warning',
    data: 'danger'
  }
  return types[category] || 'info'
}

// 获取分类名称
const getCategoryName = (category: string) => {
  const names = {
    tool: '工具类',
    entertainment: '娱乐类',
    information: '信息查询',
    data: '数据处理'
  }
  return names[category] || category
}

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('MM-DD HH:mm')
}

// 搜索处理
const handleSearch = () => {
  // 搜索是响应式的，这里可以添加额外的处理逻辑
}

// 刷新数据
const refreshData = () => {
  loadPlugins()
}

// 切换插件状态
const togglePlugin = async (plugin: any) => {
  try {
    const action = plugin.status === 'enabled' ? '禁用' : '启用'
    
    // TODO: 调用API切换插件状态
    await new Promise(resolve => setTimeout(resolve, 500))
    
    ElMessage.success(`插件${action}成功`)
  } catch (error) {
    // 回滚状态
    plugin.status = plugin.status === 'enabled' ? 'disabled' : 'enabled'
    ElMessage.error('操作失败')
  }
}

// 配置插件
const configPlugin = (plugin: any) => {
  selectedPlugin.value = plugin
  
  // 初始化配置数据
  Object.keys(plugin.settings).forEach(key => {
    const setting = plugin.settings[key]
    pluginConfig[key] = setting.default || (setting.type === 'boolean' ? false : '')
  })
  
  configDialogVisible.value = true
}

// 查看插件日志
const viewLogs = (plugin: any) => {
  ElMessage.info('插件日志功能开发中...')
}

// 卸载插件
const uninstallPlugin = async (plugin: any) => {
  try {
    // TODO: 调用API卸载插件
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 从列表中移除
    const index = pluginList.value.findIndex(p => p.id === plugin.id)
    if (index > -1) {
      pluginList.value.splice(index, 1)
    }
    
    ElMessage.success('插件卸载成功')
  } catch (error) {
    ElMessage.error('卸载失败')
  }
}

// 保存插件配置
const savePluginConfig = async () => {
  try {
    configSaving.value = true
    
    // TODO: 调用API保存插件配置
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('配置保存成功')
    configDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    configSaving.value = false
  }
}

// 关闭配置对话框
const handleConfigDialogClose = () => {
  configDialogVisible.value = false
  selectedPlugin.value = null
  Object.keys(pluginConfig).forEach(key => {
    delete pluginConfig[key]
  })
}

// 加载插件列表
const loadPlugins = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取插件列表
    await new Promise(resolve => setTimeout(resolve, 500))
  } catch (error) {
    ElMessage.error('加载插件列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPlugins()
})
</script>

<style scoped>
.plugins-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.plugin-card {
  transition: all 0.3s ease;
}

.plugin-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.plugin-card.disabled {
  opacity: 0.6;
}

.plugin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plugin-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plugin-icon {
  font-size: 20px;
}

.plugin-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.plugin-content {
  padding: 16px 0;
}

.plugin-description {
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin-bottom: 12px;
}

.plugin-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.plugin-version {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-bg-color-page);
  padding: 2px 6px;
  border-radius: 4px;
}

.plugin-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-label {
  color: var(--el-text-color-secondary);
}

.stat-value {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.plugin-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.plugin-config {
  max-height: 400px;
  overflow-y: auto;
}

.setting-description {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .plugins-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
  
  .toolbar {
    flex-direction: column;
    gap: 16px;
  }
  
  .toolbar-left {
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .plugins-grid {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>