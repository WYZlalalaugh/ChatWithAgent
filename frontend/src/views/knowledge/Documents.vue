<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">文档管理</h1>
      <div class="page-actions">
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" :icon="Plus" @click="uploadDocument">
          上传文档
        </el-button>
      </div>
    </div>

    <!-- 知识库信息 -->
    <el-card class="kb-info-card">
      <template #header>
        <span>知识库信息</span>
      </template>
      <div v-if="knowledgeBase" class="kb-info">
        <div class="info-item">
          <label>知识库名称：</label>
          <span>{{ knowledgeBase.name }}</span>
        </div>
        <div class="info-item">
          <label>描述：</label>
          <span>{{ knowledgeBase.description || '暂无描述' }}</span>
        </div>
        <div class="info-item">
          <label>文档数量：</label>
          <el-tag type="info">{{ knowledgeBase.document_count }}</el-tag>
        </div>
        <div class="info-item">
          <label>向量数量：</label>
          <el-tag type="success">{{ knowledgeBase.vector_count }}</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索文档名称..."
          :prefix-icon="Search"
          clearable
          style="width: 300px;"
          @input="handleSearch"
        />
        <el-select
          v-model="typeFilter"
          placeholder="文档类型"
          clearable
          style="width: 150px;"
          @change="handleSearch"
        >
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="docx" />
          <el-option label="文本" value="txt" />
          <el-option label="Markdown" value="md" />
        </el-select>
        <el-select
          v-model="statusFilter"
          placeholder="处理状态"
          clearable
          style="width: 120px;"
          @change="handleSearch"
        >
          <el-option label="成功" value="completed" />
          <el-option label="处理中" value="processing" />
          <el-option label="失败" value="failed" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
        <el-button :icon="Delete" @click="batchDelete" :disabled="!hasSelection">
          批量删除
        </el-button>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="content-card">
      <el-table
        v-loading="loading"
        :data="documentList"
        @selection-change="handleSelectionChange"
        stripe
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column label="文档信息" min-width="200">
          <template #default="{ row }">
            <div class="doc-info">
              <el-icon class="doc-icon" :color="getFileTypeColor(row.file_type)">
                <Document />
              </el-icon>
              <div class="doc-details">
                <div class="doc-name">{{ row.name }}</div>
                <div class="doc-meta">
                  <span class="file-size">{{ formatFileSize(row.file_size) }}</span>
                  <span class="file-type">{{ row.file_type.toUpperCase() }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="处理状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="分块数量" width="100" align="center">
          <template #default="{ row }">
            {{ row.chunk_count || 0 }}
          </template>
        </el-table-column>
        
        <el-table-column label="向量数量" width="100" align="center">
          <template #default="{ row }">
            {{ row.vector_count || 0 }}
          </template>
        </el-table-column>
        
        <el-table-column label="上传时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                @click="viewDocument(row)"
              >
                查看
              </el-button>
              
              <el-button
                v-if="row.status === 'failed'"
                size="small"
                type="warning"
                @click="reprocessDocument(row)"
              >
                重新处理
              </el-button>
              
              <el-button
                size="small"
                @click="downloadDocument(row)"
              >
                下载
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个文档吗？"
                @confirm="deleteDocument(row)"
              >
                <template #reference>
                  <el-button
                    size="small"
                    type="danger"
                  >
                    删除
                  </el-button>
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

    <!-- 上传文档对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文档"
      width="600px"
      :before-close="handleUploadDialogClose"
    >
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :multiple="true"
        :file-list="fileList"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        drag
        style="width: 100%;"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF, Word, TXT, Markdown 格式，单个文件不超过 50MB
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="fileList.length === 0"
          @click="handleUpload"
        >
          开始上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Delete, Document, UploadFilled } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

// 数据状态
const loading = ref(false)
const uploading = ref(false)
const uploadDialogVisible = ref(false)
const searchQuery = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const selectedDocuments = ref([])
const fileList = ref([])

// 知识库ID
const knowledgeBaseId = route.params.id as string

// 知识库信息
const knowledgeBase = ref<any>(null)

// 上传引用
const uploadRef = ref()

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 文档列表数据（模拟数据）
const documentList = ref([
  {
    id: '1',
    name: '产品介绍手册.pdf',
    file_type: 'pdf',
    file_size: 2048576, // 2MB
    status: 'completed',
    chunk_count: 25,
    vector_count: 25,
    created_at: '2024-01-10T14:30:00Z'
  },
  {
    id: '2',
    name: '用户指南.docx',
    file_type: 'docx',
    file_size: 1024000, // 1MB
    status: 'processing',
    chunk_count: 0,
    vector_count: 0,
    created_at: '2024-01-10T13:15:00Z'
  },
  {
    id: '3',
    name: 'FAQ.md',
    file_type: 'md',
    file_size: 51200, // 50KB
    status: 'failed',
    chunk_count: 0,
    vector_count: 0,
    created_at: '2024-01-10T12:00:00Z'
  }
])

// 计算属性
const hasSelection = computed(() => selectedDocuments.value.length > 0)

// 获取文件类型颜色
const getFileTypeColor = (type: string) => {
  const colors = {
    pdf: '#f56c6c',
    docx: '#409eff',
    txt: '#67c23a',
    md: '#e6a23c'
  }
  return colors[type] || '#909399'
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const types = {
    completed: 'success',
    processing: 'warning',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts = {
    completed: '成功',
    processing: '处理中',
    failed: '失败'
  }
  return texts[status] || status
}

// 格式化文件大小
const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  loadDocuments()
}

// 刷新数据
const refreshData = () => {
  loadDocuments()
  loadKnowledgeBaseInfo()
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedDocuments.value = selection
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  loadDocuments()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadDocuments()
}

// 上传文档
const uploadDocument = () => {
  fileList.value = []
  uploadDialogVisible.value = true
}

// 文件变化处理
const handleFileChange = (file: any, files: any[]) => {
  // 检查文件类型
  const allowedTypes = ['pdf', 'docx', 'txt', 'md']
  const fileExt = file.name.split('.').pop()?.toLowerCase()
  
  if (!allowedTypes.includes(fileExt)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  
  // 检查文件大小
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  
  fileList.value = files
}

// 移除文件
const handleFileRemove = (file: any, files: any[]) => {
  fileList.value = files
}

// 执行上传
const handleUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  
  try {
    uploading.value = true
    
    // TODO: 调用API上传文件
    for (const file of fileList.value) {
      const formData = new FormData()
      formData.append('file', file.raw)
      formData.append('knowledge_base_id', knowledgeBaseId)
      
      // 模拟上传延迟
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    ElMessage.success('文档上传成功，正在处理中...')
    uploadDialogVisible.value = false
    loadDocuments()
    
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 关闭上传对话框
const handleUploadDialogClose = () => {
  uploadDialogVisible.value = false
  fileList.value = []
}

// 查看文档
const viewDocument = (doc: any) => {
  ElMessage.info('文档查看功能开发中...')
}

// 重新处理文档
const reprocessDocument = async (doc: any) => {
  try {
    await ElMessageBox.confirm(`确定要重新处理文档"${doc.name}"吗？`, '确认')
    
    // TODO: 调用API重新处理
    doc.status = 'processing'
    ElMessage.success('已开始重新处理')
  } catch {
    // 用户取消
  }
}

// 下载文档
const downloadDocument = (doc: any) => {
  ElMessage.info('文档下载功能开发中...')
}

// 删除文档
const deleteDocument = async (doc: any) => {
  try {
    // TODO: 调用API删除
    ElMessage.success('删除成功')
    loadDocuments()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 批量删除
const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedDocuments.value.length} 个文档吗？`,
      '确认',
      { type: 'warning' }
    )
    
    // TODO: 调用API批量删除
    ElMessage.success('批量删除成功')
    loadDocuments()
  } catch {
    // 用户取消
  }
}

// 加载知识库信息
const loadKnowledgeBaseInfo = async () => {
  try {
    // TODO: 调用API获取知识库信息
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // 模拟数据
    knowledgeBase.value = {
      id: knowledgeBaseId,
      name: '产品手册',
      description: '包含产品功能介绍、使用指南等文档',
      document_count: documentList.value.length,
      vector_count: documentList.value.reduce((sum, doc) => sum + (doc.vector_count || 0), 0)
    }
  } catch (error) {
    ElMessage.error('加载知识库信息失败')
  }
}

// 加载文档列表
const loadDocuments = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取数据
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用过滤器
    let filteredList = [...documentList.value]
    
    if (searchQuery.value) {
      filteredList = filteredList.filter(doc => 
        doc.name.toLowerCase().includes(searchQuery.value.toLowerCase())
      )
    }
    
    if (typeFilter.value) {
      filteredList = filteredList.filter(doc => doc.file_type === typeFilter.value)
    }
    
    if (statusFilter.value) {
      filteredList = filteredList.filter(doc => doc.status === statusFilter.value)
    }
    
    // 更新分页信息
    pagination.total = filteredList.length
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadKnowledgeBaseInfo()
  loadDocuments()
})
</script>

<style scoped>
.kb-info-card {
  margin-bottom: 24px;
}

.kb-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item label {
  font-weight: 500;
  color: var(--el-text-color-secondary);
  min-width: 80px;
}

.doc-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-icon {
  flex-shrink: 0;
  font-size: 24px;
}

.doc-details {
  flex: 1;
  min-width: 0;
}

.doc-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.file-size,
.file-type {
  padding: 2px 6px;
  background: var(--el-bg-color-page);
  border-radius: 4px;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
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
  
  .kb-info {
    grid-template-columns: 1fr;
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