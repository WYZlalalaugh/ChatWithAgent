<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <div class="page-actions">
        <el-button type="primary" :icon="Plus" @click="createUser">
          新建用户
        </el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名称..."
          :prefix-icon="Search"
          clearable
          style="width: 300px;"
          @input="handleSearch"
        />
        <el-select
          v-model="roleFilter"
          placeholder="角色"
          clearable
          style="width: 150px;"
          @change="handleSearch"
        >
          <el-option label="管理员" value="admin" />
          <el-option label="普通用户" value="user" />
        </el-select>
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

    <!-- 用户列表 -->
    <div class="content-card">
      <el-table
        v-loading="loading"
        :data="userList"
        stripe
        style="width: 100%"
      >
        <el-table-column label="用户信息" min-width="200">
          <template #default="{ row }">
            <div class="user-info">
              <el-avatar :src="row.avatar_url" :size="40">
                {{ row.nickname?.charAt(0) || row.username?.charAt(0) }}
              </el-avatar>
              <div class="user-details">
                <div class="user-name">{{ row.nickname || row.username }}</div>
                <div class="user-email">{{ row.email }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="用户名" prop="username" width="150" />
        
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="最后登录" width="150">
          <template #default="{ row }">
            {{ row.last_login ? formatTime(row.last_login) : '从未登录' }}
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
              <el-button
                size="small"
                @click="editUser(row)"
              >
                编辑
              </el-button>
              
              <el-button
                size="small"
                :type="row.status === 'active' ? 'warning' : 'success'"
                @click="toggleUserStatus(row)"
              >
                {{ row.status === 'active' ? '禁用' : '启用' }}
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个用户吗？"
                @confirm="deleteUser(row)"
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

    <!-- 用户表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      :before-close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="userForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="userForm.username"
            placeholder="请输入用户名"
            :disabled="!!userForm.id"
          />
        </el-form-item>
        
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="userForm.nickname" placeholder="请输入昵称" />
        </el-form-item>
        
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        
        <el-form-item v-if="!userForm.id" label="密码" prop="password">
          <el-input
            v-model="userForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="状态" prop="status">
          <el-switch
            v-model="userForm.status"
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
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// 数据状态
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const searchQuery = ref('')
const roleFilter = ref('')
const statusFilter = ref('')

// 表单引用
const formRef = ref<FormInstance>()

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 用户表单数据
const userForm = reactive({
  id: '',
  username: '',
  nickname: '',
  email: '',
  password: '',
  role: 'user',
  status: 'active'
})

// 表单验证规则
const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

// 用户列表数据（模拟数据）
const userList = ref([
  {
    id: '1',
    username: 'admin',
    nickname: '系统管理员',
    email: 'admin@chatagent.com',
    avatar_url: '',
    role: 'admin',
    status: 'active',
    last_login: '2024-01-10T14:30:00Z',
    created_at: '2024-01-01T10:00:00Z'
  },
  {
    id: '2',
    username: 'user001',
    nickname: '张三',
    email: 'zhangsan@example.com',
    avatar_url: '',
    role: 'user',
    status: 'active',
    last_login: '2024-01-10T12:15:00Z',
    created_at: '2024-01-05T14:20:00Z'
  },
  {
    id: '3',
    username: 'user002',
    nickname: '李四',
    email: 'lisi@example.com',
    avatar_url: '',
    role: 'user',
    status: 'inactive',
    last_login: null,
    created_at: '2024-01-08T09:30:00Z'
  }
])

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 搜索处理
const handleSearch = () => {
  pagination.page = 1
  loadUsers()
}

// 刷新数据
const refreshData = () => {
  loadUsers()
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  loadUsers()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  loadUsers()
}

// 创建用户
const createUser = () => {
  dialogTitle.value = '新建用户'
  resetForm()
  dialogVisible.value = true
}

// 编辑用户
const editUser = (user: any) => {
  dialogTitle.value = '编辑用户'
  Object.assign(userForm, {
    id: user.id,
    username: user.username,
    nickname: user.nickname,
    email: user.email,
    password: '',
    role: user.role,
    status: user.status
  })
  dialogVisible.value = true
}

// 切换用户状态
const toggleUserStatus = async (user: any) => {
  try {
    const action = user.status === 'active' ? '禁用' : '启用'
    await ElMessageBox.confirm(`确定要${action}用户"${user.nickname}"吗？`, '确认')
    
    // TODO: 调用API切换状态
    user.status = user.status === 'active' ? 'inactive' : 'active'
    ElMessage.success(`${action}成功`)
  } catch {
    // 用户取消
  }
}

// 删除用户
const deleteUser = async (user: any) => {
  try {
    // TODO: 调用API删除
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(userForm, {
    id: '',
    username: '',
    nickname: '',
    email: '',
    password: '',
    role: 'user',
    status: 'active'
  })
  formRef.value?.clearValidate()
}

// 关闭对话框
const handleDialogClose = () => {
  dialogVisible.value = false
  resetForm()
}

// 保存用户
const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    saving.value = true
    
    // TODO: 调用API保存用户
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success(userForm.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadUsers()
  } catch (error) {
    if (error !== false) {
      ElMessage.error('保存失败，请检查表单')
    }
  } finally {
    saving.value = false
  }
}

// 加载用户列表
const loadUsers = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取数据
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用过滤器
    let filteredUsers = [...userList.value]
    
    if (searchQuery.value) {
      filteredUsers = filteredUsers.filter(user => 
        user.nickname.includes(searchQuery.value) || 
        user.username.includes(searchQuery.value) ||
        user.email.includes(searchQuery.value)
      )
    }
    
    if (roleFilter.value) {
      filteredUsers = filteredUsers.filter(user => user.role === roleFilter.value)
    }
    
    if (statusFilter.value) {
      filteredUsers = filteredUsers.filter(user => user.status === statusFilter.value)
    }
    
    // 更新分页信息
    pagination.total = filteredUsers.length
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-details {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.user-email {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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