<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">知识库管理</h1>
      <div class="page-actions">
        <el-button type="primary" :icon="Plus" @click="createKnowledgeBase">
          新建知识库
        </el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索知识库名称..."
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
          <el-option label="正常" value="active" />
          <el-option label="禁用" value="inactive" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
      </div>
    </div>

    <!-- 知识库列表 -->
    <div class="content-card">
      <el-table
        v-loading="loading"
        :data="knowledgeBaseList"
        stripe
        style="width: 100%"
      >
        <el-table-column label="知识库信息" min-width="200">
          <template #default="{ row }">
            <div class="kb-info">
              <el-icon class="kb-icon" size="32" color="#409eff">
                <Collection />
              </el-icon>
              <div class="kb-details">
                <div class="kb-name">{{ row.name }}</div>
                <div class="kb-description">{{ row.description || '暂无描述' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="文档数量" width="120" align="center">
          <template #default="{ row }">
            <el-tag type="info">{{ row.document_count }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="向量数量" width="120" align="center">
          <template #default="{ row }">
            <el-tag type="success">{{ row.vector_count }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="最后更新" width="150">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                @click="viewDocuments(row)"
              >
                查看文档
              </el-button>
              
              <el-button
                size="small"
                @click="editKnowledgeBase(row)"
              >
                编辑
              </el-button>
              
              <el-button
                size="small"
                :type="row.status === 'active' ? 'warning' : 'success'"
                @click="toggleStatus(row)"
              >
                {{ row.status === 'active' ? '禁用' : '启用' }}
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个知识库吗？"
                @confirm="deleteKnowledgeBase(row)"
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

    <!-- 知识库表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :before-close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="kbForm"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="知识库名称" prop="name">
          <el-input
            v-model="kbForm.name"
            placeholder="请输入知识库名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input
            v-model="kbForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="向量模型" prop="embedding_model">
          <el-select v-model="kbForm.embedding_model" placeholder="请选择向量模型">
            <el-option label="text-embedding-ada-002" value="text-embedding-ada-002" />
            <el-option label="text-embedding-3-small" value="text-embedding-3-small" />
            <el-option label="text-embedding-3-large" value="text-embedding-3-large" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="向量维度">
          <el-input-number
            v-model="kbForm.vector_dimension"
            :min="128"
            :max="3072"
            :step="64"
            style="width: 200px;"
          />
        </el-form-item>
        
        <el-form-item label="分块大小">
          <el-input-number
            v-model="kbForm.chunk_size"
            :min="100"
            :max="2000"
            :step="100"
            style="width: 200px;"
          />
          <div class="param-description">
            文档分块的大小，影响检索精度和效率
          </div>
        </el-form-item>
        
        <el-form-item label="分块重叠">
          <el-input-number
            v-model="kbForm.chunk_overlap"
            :min="0"
            :max="500"
            :step="10"
            style="width: 200px;"
          />
          <div class="param-description">
            相邻分块之间的重叠字符数
          </div>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch
            v-model="kbForm.status"
            active-value="active"
            inactive-value="inactive"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Search, Refresh, Collection } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()

// 数据状态
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const searchQuery = ref('')
const statusFilter = ref('')

// 表单引用
const formRef = ref<FormInstance>()

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 知识库表单数据
const kbForm = reactive({
  id: '',
  name: '',
  description: '',
  embedding_model: 'text-embedding-ada-002',
  vector_dimension: 1536,
  chunk_size: 1000,
  chunk_overlap: 100,
  status: 'active'
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度为2-50个字符', trigger: 'blur' }
  ],
  embedding_model: [
    { required: true, message: '请选择向量模型', trigger: 'change' }
  ]
}

// 知识库列表数据（模拟数据）
const knowledgeBaseList = ref([
  {
    id: '1',
    name: '产品手册',
    description: '包含产品功能介绍、使用指南等文档',
    document_count: 25,
    vector_count: 1205,
    status: 'active',
    embedding_model: 'text-embedding-ada-002',
    created_at: '2024-01-05T10:00:00Z',
    updated_at: '2024-01-10T14:30:00Z'
  },
  {
    id: '2',
    name: '常见问题',
    description: 'FAQ和常见问题解答',
    document_count: 15,
    vector_count: 486,
    status: 'active',
    embedding_model: 'text-embedding-ada-002',
    created_at: '2024-01-03T09:30:00Z',
    updated_at: '2024-01-09T16:45:00Z'
  },
  {
    id: '3',
    name: '技术文档',
    description: '技术规范和开发文档',
    document_count: 8,
    vector_count: 324,
    status: 'inactive',
    embedding_model: 'text-embedding-ada-002',
    created_at: '2024-01-01T14:20:00Z',
    updated_at: '2024-01-08T11:15:00Z'
  }
])

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  loadKnowledgeBases()
}

// 刷新数据
const refreshData = () => {
  loadKnowledgeBases()
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  loadKnowledgeBases()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadKnowledgeBases()
}

// 创建知识库
const createKnowledgeBase = () => {
  dialogTitle.value = '新建知识库'
  resetForm()
  dialogVisible.value = true
}

// 编辑知识库
const editKnowledgeBase = (kb: any) => {
  dialogTitle.value = '编辑知识库'
  Object.assign(kbForm, {
    id: kb.id,
    name: kb.name,
    description: kb.description,
    embedding_model: kb.embedding_model,
    vector_dimension: 1536,
    chunk_size: 1000,
    chunk_overlap: 100,
    status: kb.status
  })
  dialogVisible.value = true
}

// 查看文档
const viewDocuments = (kb: any) => {
  router.push(`/knowledge/bases/${kb.id}/documents`)
}

// 切换状态
const toggleStatus = async (kb: any) => {
  try {
    const action = kb.status === 'active' ? '禁用' : '启用'
    await ElMessageBox.confirm(`确定要${action}知识库"${kb.name}"吗？`, '确认')
    
    // TODO: 调用API切换状态
    kb.status = kb.status === 'active' ? 'inactive' : 'active'
    ElMessage.success(`${action}成功`)
  } catch {
    // 用户取消
  }
}

// 删除知识库
const deleteKnowledgeBase = async (kb: any) => {
  try {
    // TODO: 调用API删除
    ElMessage.success('删除成功')
    loadKnowledgeBases()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(kbForm, {
    id: '',
    name: '',
    description: '',
    embedding_model: 'text-embedding-ada-002',
    vector_dimension: 1536,
    chunk_size: 1000,
    chunk_overlap: 100,
    status: 'active'
  })
  formRef.value?.clearValidate()
}

// 关闭对话框
const handleDialogClose = () => {
  dialogVisible.value = false
  resetForm()
}

// 保存知识库
const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    saving.value = true
    
    // TODO: 调用API保存知识库
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success(kbForm.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadKnowledgeBases()
  } catch (error) {
    if (error !== false) {
      ElMessage.error('保存失败，请检查表单')
    }
  } finally {
    saving.value = false
  }
}

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取数据
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用过滤器
    let filteredList = [...knowledgeBaseList.value]
    
    if (searchQuery.value) {
      filteredList = filteredList.filter(kb => 
        kb.name.includes(searchQuery.value) || 
        (kb.description && kb.description.includes(searchQuery.value))
      )
    }
    
    if (statusFilter.value) {
      filteredList = filteredList.filter(kb => kb.status === statusFilter.value)
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
  loadKnowledgeBases()
})
</script>

<style scoped>
.kb-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-icon {
  flex-shrink: 0;
}

.kb-details {
  flex: 1;
  min-width: 0;
}

.kb-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.kb-description {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.param-description {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
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