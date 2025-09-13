<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">插件市场</h1>
      <div class="page-actions">
        <el-button @click="$router.push('/plugins/installed')">
          已安装插件
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="marketplace-header">
      <div class="search-section">
        <el-input
          v-model="searchQuery"
          placeholder="搜索插件名称或描述..."
          :prefix-icon="Search"
          clearable
          size="large"
          style="max-width: 400px;"
          @input="handleSearch"
        />
      </div>
      
      <div class="filter-section">
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
        
        <el-select
          v-model="sortBy"
          placeholder="排序方式"
          style="width: 150px;"
          @change="handleSort"
        >
          <el-option label="最新发布" value="latest" />
          <el-option label="最受欢迎" value="popular" />
          <el-option label="评分最高" value="rating" />
          <el-option label="下载最多" value="downloads" />
        </el-select>
      </div>
    </div>

    <!-- 插件列表 -->
    <div v-loading="loading" class="marketplace-content">
      <div class="plugins-grid">
        <el-card
          v-for="plugin in filteredPluginList"
          :key="plugin.id"
          class="plugin-card"
        >
          <template #header>
            <div class="plugin-header">
              <div class="plugin-title">
                <el-icon class="plugin-icon" :color="plugin.icon_color">
                  <component :is="plugin.icon" />
                </el-icon>
                <div class="plugin-title-text">
                  <h3>{{ plugin.name }}</h3>
                  <span class="plugin-author">by {{ plugin.author }}</span>
                </div>
              </div>
              <el-tag :type="getCategoryTagType(plugin.category)" size="small">
                {{ getCategoryName(plugin.category) }}
              </el-tag>
            </div>
          </template>
          
          <div class="plugin-content">
            <div class="plugin-description">
              {{ plugin.description }}
            </div>
            
            <div class="plugin-stats">
              <div class="stat-item">
                <el-icon><Star /></el-icon>
                <span>{{ plugin.rating }}</span>
              </div>
              <div class="stat-item">
                <el-icon><Download /></el-icon>
                <span>{{ formatDownloads(plugin.downloads) }}</span>
              </div>
              <div class="stat-item">
                <span class="version">v{{ plugin.version }}</span>
              </div>
            </div>
            
            <div class="plugin-tags">
              <el-tag
                v-for="tag in plugin.tags"
                :key="tag"
                size="small"
                effect="plain"
                style="margin-right: 8px; margin-bottom: 4px;"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>
          
          <template #footer>
            <div class="plugin-actions">
              <el-button
                v-if="!plugin.installed"
                type="primary"
                :loading="plugin.installing"
                @click="installPlugin(plugin)"
              >
                安装
              </el-button>
              <el-button
                v-else
                type="info"
                disabled
              >
                已安装
              </el-button>
              <el-button @click="viewPluginDetail(plugin)">
                详情
              </el-button>
            </div>
          </template>
        </el-card>
      </div>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[12, 24, 48]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 插件详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="selectedPlugin?.name"
      width="70%"
      :before-close="handleDetailDialogClose"
    >
      <div v-if="selectedPlugin" class="plugin-detail">
        <div class="detail-header">
          <div class="plugin-basic-info">
            <el-icon class="detail-icon" :color="selectedPlugin.icon_color" size="48">
              <component :is="selectedPlugin.icon" />
            </el-icon>
            <div class="basic-info-text">
              <h2>{{ selectedPlugin.name }}</h2>
              <p class="author">作者: {{ selectedPlugin.author }}</p>
              <p class="version">版本: v{{ selectedPlugin.version }}</p>
            </div>
          </div>
          
          <div class="plugin-metrics">
            <div class="metric-item">
              <span class="metric-label">评分</span>
              <div class="metric-value">
                <el-rate v-model="selectedPlugin.rating" disabled show-score />
              </div>
            </div>
            <div class="metric-item">
              <span class="metric-label">下载量</span>
              <span class="metric-value">{{ formatDownloads(selectedPlugin.downloads) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">更新时间</span>
              <span class="metric-value">{{ formatTime(selectedPlugin.updated_at) }}</span>
            </div>
          </div>
        </div>
        
        <el-divider />
        
        <div class="detail-content">
          <h3>插件描述</h3>
          <div class="plugin-description-detail">
            {{ selectedPlugin.detailed_description || selectedPlugin.description }}
          </div>
          
          <h3>功能特性</h3>
          <ul class="feature-list">
            <li v-for="feature in selectedPlugin.features" :key="feature">
              {{ feature }}
            </li>
          </ul>
          
          <h3>使用说明</h3>
          <div class="usage-guide">
            {{ selectedPlugin.usage_guide || '暂无使用说明' }}
          </div>
          
          <h3>更新日志</h3>
          <div class="changelog">
            <div
              v-for="change in selectedPlugin.changelog"
              :key="change.version"
              class="changelog-item"
            >
              <h4>v{{ change.version }}</h4>
              <p class="change-date">{{ formatTime(change.date) }}</p>
              <ul>
                <li v-for="item in change.changes" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button
          v-if="selectedPlugin && !selectedPlugin.installed"
          type="primary"
          :loading="selectedPlugin.installing"
          @click="installPlugin(selectedPlugin)"
        >
          安装插件
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search,
  Star,
  Download,
  Setting,
  Document,
  ChatDotRound,
  Coordinate,
  DataAnalysis,
  VideoPlay
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()

// 数据状态
const loading = ref(false)
const detailDialogVisible = ref(false)
const searchQuery = ref('')
const categoryFilter = ref('')
const sortBy = ref('latest')
const selectedPlugin = ref<any>(null)

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 12,
  total: 0
})

// 插件市场数据（模拟数据）
const marketplacePlugins = ref([
  {
    id: '1',
    name: '天气查询',
    author: 'ChatAgent官方',
    description: '查询全球各地的天气信息，支持实时天气和天气预报',
    detailed_description: '这是一个功能强大的天气查询插件，可以帮助用户快速获取全球任意城市的天气信息。支持实时天气查询、7天天气预报、空气质量指数等功能。',
    category: 'information',
    version: '1.2.0',
    rating: 4.8,
    downloads: 15420,
    installed: true,
    installing: false,
    icon: 'Coordinate',
    icon_color: '#409eff',
    tags: ['天气', '查询', '实用'],
    features: [
      '支持全球城市天气查询',
      '提供7天天气预报',
      '显示空气质量指数',
      '支持多种温度单位',
      '自动定位当前城市'
    ],
    usage_guide: '直接输入"天气 城市名"即可查询该城市的天气信息，例如："天气 北京"',
    changelog: [
      {
        version: '1.2.0',
        date: '2024-01-10T10:00:00Z',
        changes: [
          '新增空气质量指数显示',
          '优化查询响应速度',
          '修复部分城市无法查询的问题'
        ]
      },
      {
        version: '1.1.0',
        date: '2024-01-01T10:00:00Z',
        changes: [
          '新增7天天气预报',
          '支持自动定位',
          '改进用户界面'
        ]
      }
    ],
    updated_at: '2024-01-10T10:00:00Z'
  },
  {
    id: '2',
    name: '快递查询',
    author: 'ChatAgent官方',
    description: '查询各大快递公司的物流信息',
    category: 'information',
    version: '1.0.5',
    rating: 4.6,
    downloads: 8950,
    installed: true,
    installing: false,
    icon: 'Document',
    icon_color: '#67c23a',
    tags: ['快递', '物流', '查询'],
    features: [
      '支持主流快递公司',
      '自动识别快递公司',
      '实时物流跟踪',
      '配送状态提醒'
    ],
    usage_guide: '输入"快递 单号"即可查询物流信息',
    changelog: [],
    updated_at: '2024-01-05T10:00:00Z'
  },
  {
    id: '3',
    name: '翻译助手',
    author: 'ChatAgent官方',
    description: '多语言翻译工具，支持100+种语言互译',
    category: 'tool',
    version: '2.1.0',
    rating: 4.9,
    downloads: 25680,
    installed: false,
    installing: false,
    icon: 'ChatDotRound',
    icon_color: '#e6a23c',
    tags: ['翻译', '多语言', '工具'],
    features: [
      '支持100+种语言',
      '智能语言检测',
      '批量翻译功能',
      '翻译历史记录'
    ],
    usage_guide: '输入"翻译 要翻译的文本"或"translate hello to chinese"',
    changelog: [],
    updated_at: '2024-01-08T10:00:00Z'
  },
  {
    id: '4',
    name: '数据分析',
    author: 'DataViz Studio',
    description: '对数据进行统计分析和可视化',
    category: 'data',
    version: '1.5.2',
    rating: 4.7,
    downloads: 5240,
    installed: false,
    installing: false,
    icon: 'DataAnalysis',
    icon_color: '#f56c6c',
    tags: ['数据', '分析', '可视化'],
    features: [
      '统计分析功能',
      '图表可视化',
      '数据导入导出',
      '自定义分析模板'
    ],
    usage_guide: '上传数据文件后，选择分析类型即可生成分析报告',
    changelog: [],
    updated_at: '2024-01-07T10:00:00Z'
  },
  {
    id: '5',
    name: '音乐播放器',
    author: 'Music Labs',
    description: '在线音乐播放和推荐系统',
    category: 'entertainment',
    version: '3.0.1',
    rating: 4.5,
    downloads: 12350,
    installed: false,
    installing: false,
    icon: 'VideoPlay',
    icon_color: '#9c27b0',
    tags: ['音乐', '播放器', '娱乐'],
    features: [
      '海量音乐资源',
      '智能推荐算法',
      '歌词同步显示',
      '个性化播放列表'
    ],
    usage_guide: '输入"播放 歌曲名"或"音乐推荐"获取音乐服务',
    changelog: [],
    updated_at: '2024-01-09T10:00:00Z'
  },
  {
    id: '6',
    name: '股票查询',
    author: 'Finance Pro',
    description: '实时股票行情和财经信息查询',
    category: 'information',
    version: '2.3.0',
    rating: 4.4,
    downloads: 7890,
    installed: false,
    installing: false,
    icon: 'DataAnalysis',
    icon_color: '#00bcd4',
    tags: ['股票', '财经', '投资'],
    features: [
      '实时行情数据',
      '技术指标分析',
      '财经新闻推送',
      '投资组合管理'
    ],
    usage_guide: '输入"股票 股票代码"查询股票信息',
    changelog: [],
    updated_at: '2024-01-06T10:00:00Z'
  }
])

// 计算属性 - 过滤后的插件列表
const filteredPluginList = computed(() => {
  let filtered = [...marketplacePlugins.value]
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(plugin => 
      plugin.name.toLowerCase().includes(query) ||
      plugin.description.toLowerCase().includes(query) ||
      plugin.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }
  
  // 分类过滤
  if (categoryFilter.value) {
    filtered = filtered.filter(plugin => plugin.category === categoryFilter.value)
  }
  
  // 排序
  switch (sortBy.value) {
    case 'popular':
      filtered.sort((a, b) => b.downloads - a.downloads)
      break
    case 'rating':
      filtered.sort((a, b) => b.rating - a.rating)
      break
    case 'downloads':
      filtered.sort((a, b) => b.downloads - a.downloads)
      break
    case 'latest':
    default:
      filtered.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      break
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

// 格式化下载量
const formatDownloads = (downloads: number) => {
  if (downloads < 1000) return downloads.toString()
  if (downloads < 10000) return `${(downloads / 1000).toFixed(1)}k`
  return `${(downloads / 10000).toFixed(1)}w`
}

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD')
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  pagination.total = filteredPluginList.value.length
}

// 排序处理
const handleSort = () => {
  pagination.page = 1
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
}

// 安装插件
const installPlugin = async (plugin: any) => {
  try {
    plugin.installing = true
    
    // TODO: 调用API安装插件
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    plugin.installed = true
    plugin.downloads += 1
    ElMessage.success(`插件"${plugin.name}"安装成功`)
  } catch (error) {
    ElMessage.error('插件安装失败')
  } finally {
    plugin.installing = false
  }
}

// 查看插件详情
const viewPluginDetail = (plugin: any) => {
  selectedPlugin.value = plugin
  detailDialogVisible.value = true
}

// 关闭详情对话框
const handleDetailDialogClose = () => {
  detailDialogVisible.value = false
  selectedPlugin.value = null
}

// 加载插件市场数据
const loadMarketplace = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取插件市场数据
    await new Promise(resolve => setTimeout(resolve, 500))
    
    pagination.total = filteredPluginList.value.length
  } catch (error) {
    ElMessage.error('加载插件市场失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMarketplace()
})
</script>

<style scoped>
.marketplace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
}

.search-section {
  flex: 1;
}

.filter-section {
  display: flex;
  gap: 12px;
}

.marketplace-content {
  min-height: 400px;
}

.plugins-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.plugin-card {
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.plugin-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.plugin-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.plugin-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.plugin-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.plugin-title-text h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.plugin-author {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.plugin-content {
  flex: 1;
  padding: 16px 0;
}

.plugin-description {
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin-bottom: 16px;
  height: 48px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.plugin-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.version {
  background: var(--el-bg-color-page);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.plugin-tags {
  margin-bottom: 16px;
}

.plugin-actions {
  display: flex;
  gap: 8px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

/* 插件详情样式 */
.plugin-detail {
  max-height: 600px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.plugin-basic-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.detail-icon {
  flex-shrink: 0;
}

.basic-info-text h2 {
  margin: 0 0 8px 0;
  color: var(--el-text-color-primary);
}

.author,
.version {
  margin: 4px 0;
  color: var(--el-text-color-secondary);
}

.plugin-metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: right;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.metric-value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.detail-content h3 {
  margin: 20px 0 12px 0;
  color: var(--el-text-color-primary);
}

.plugin-description-detail,
.usage-guide {
  line-height: 1.6;
  color: var(--el-text-color-regular);
  margin-bottom: 16px;
}

.feature-list {
  margin: 0 0 16px 20px;
  color: var(--el-text-color-regular);
}

.feature-list li {
  margin-bottom: 8px;
}

.changelog {
  max-height: 200px;
  overflow-y: auto;
}

.changelog-item {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.changelog-item:last-child {
  border-bottom: none;
}

.changelog-item h4 {
  margin: 0 0 4px 0;
  color: var(--el-text-color-primary);
}

.change-date {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px 0;
}

.changelog-item ul {
  margin: 0 0 0 20px;
  color: var(--el-text-color-regular);
}

.changelog-item li {
  margin-bottom: 4px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .plugins-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
  
  .marketplace-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .filter-section {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .plugins-grid {
    grid-template-columns: 1fr;
  }
  
  .detail-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .plugin-metrics {
    flex-direction: row;
    text-align: left;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>