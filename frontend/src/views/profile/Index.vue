<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">个人中心</h1>
    </div>

    <div class="profile-container">
      <!-- 个人信息卡片 -->
      <el-card class="profile-card">
        <template #header>
          <span>个人信息</span>
        </template>
        
        <div class="profile-info">
          <div class="avatar-section">
            <el-upload
              class="avatar-uploader"
              action="#"
              :show-file-list="false"
              :before-upload="beforeAvatarUpload"
              :http-request="handleAvatarUpload"
            >
              <el-avatar :src="userInfo.avatar_url" :size="100">
                {{ userInfo.nickname?.charAt(0) || userInfo.username?.charAt(0) }}
              </el-avatar>
              <div class="avatar-overlay">
                <el-icon><Camera /></el-icon>
              </div>
            </el-upload>
          </div>
          
          <div class="info-section">
            <el-form
              ref="profileFormRef"
              :model="userInfo"
              :rules="profileRules"
              label-width="100px"
            >
              <el-form-item label="用户名">
                <el-input v-model="userInfo.username" disabled />
              </el-form-item>
              
              <el-form-item label="昵称" prop="nickname">
                <el-input
                  v-model="userInfo.nickname"
                  placeholder="请输入昵称"
                  :disabled="!editingProfile"
                />
              </el-form-item>
              
              <el-form-item label="邮箱" prop="email">
                <el-input
                  v-model="userInfo.email"
                  placeholder="请输入邮箱"
                  :disabled="!editingProfile"
                />
              </el-form-item>
              
              <el-form-item label="手机号" prop="phone">
                <el-input
                  v-model="userInfo.phone"
                  placeholder="请输入手机号"
                  :disabled="!editingProfile"
                />
              </el-form-item>
              
              <el-form-item label="个人简介">
                <el-input
                  v-model="userInfo.bio"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入个人简介"
                  :disabled="!editingProfile"
                  maxlength="200"
                  show-word-limit
                />
              </el-form-item>
              
              <el-form-item>
                <el-button
                  v-if="!editingProfile"
                  type="primary"
                  @click="editingProfile = true"
                >
                  编辑信息
                </el-button>
                <template v-else>
                  <el-button
                    type="primary"
                    :loading="savingProfile"
                    @click="saveProfile"
                  >
                    保存
                  </el-button>
                  <el-button @click="cancelEdit">取消</el-button>
                </template>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </el-card>

      <!-- 安全设置卡片 -->
      <el-card class="security-card">
        <template #header>
          <span>安全设置</span>
        </template>
        
        <div class="security-settings">
          <div class="security-item">
            <div class="security-info">
              <h4>登录密码</h4>
              <p>定期更换密码可以提高账户安全性</p>
            </div>
            <el-button @click="showChangePasswordDialog">修改密码</el-button>
          </div>
          
          <el-divider />
          
          <div class="security-item">
            <div class="security-info">
              <h4>两步验证</h4>
              <p>开启后登录时需要验证码，提高账户安全性</p>
            </div>
            <el-switch
              v-model="userInfo.two_factor_enabled"
              @change="toggleTwoFactor"
            />
          </div>
          
          <el-divider />
          
          <div class="security-item">
            <div class="security-info">
              <h4>登录记录</h4>
              <p>查看最近的登录记录和设备信息</p>
            </div>
            <el-button @click="showLoginHistory">查看记录</el-button>
          </div>
        </div>
      </el-card>

      <!-- 偏好设置卡片 -->
      <el-card class="preferences-card">
        <template #header>
          <span>偏好设置</span>
        </template>
        
        <div class="preferences-settings">
          <el-form label-width="120px">
            <el-form-item label="主题模式">
              <el-radio-group v-model="preferences.theme">
                <el-radio label="light">浅色主题</el-radio>
                <el-radio label="dark">深色主题</el-radio>
                <el-radio label="auto">跟随系统</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="语言设置">
              <el-select v-model="preferences.language" style="width: 200px;">
                <el-option label="中文简体" value="zh-CN" />
                <el-option label="中文繁体" value="zh-TW" />
                <el-option label="English" value="en-US" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="邮件通知">
              <el-checkbox-group v-model="preferences.email_notifications">
                <el-checkbox label="system">系统通知</el-checkbox>
                <el-checkbox label="security">安全提醒</el-checkbox>
                <el-checkbox label="updates">功能更新</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-form-item label="声音提示">
              <el-switch v-model="preferences.sound_enabled" />
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                :loading="savingPreferences"
                @click="savePreferences"
              >
                保存偏好
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-card>

      <!-- 统计信息卡片 -->
      <el-card class="stats-card">
        <template #header>
          <span>使用统计</span>
        </template>
        
        <div class="user-stats">
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-icon">
                <el-icon color="#409eff"><ChatDotRound /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ userStats.total_conversations }}</div>
                <div class="stat-label">总对话数</div>
              </div>
            </div>
            
            <div class="stat-item">
              <div class="stat-icon">
                <el-icon color="#67c23a"><Message /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ userStats.total_messages }}</div>
                <div class="stat-label">总消息数</div>
              </div>
            </div>
            
            <div class="stat-item">
              <div class="stat-icon">
                <el-icon color="#e6a23c"><Timer /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ userStats.total_time }}</div>
                <div class="stat-label">使用时长</div>
              </div>
            </div>
            
            <div class="stat-item">
              <div class="stat-icon">
                <el-icon color="#f56c6c"><Calendar /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ userStats.days_active }}</div>
                <div class="stat-label">活跃天数</div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="400px"
      :before-close="handlePasswordDialogClose"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="当前密码" prop="currentPassword">
          <el-input
            v-model="passwordForm.currentPassword"
            type="password"
            placeholder="请输入当前密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="changingPassword"
          @click="changePassword"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>

    <!-- 登录记录对话框 -->
    <el-dialog
      v-model="loginHistoryDialogVisible"
      title="登录记录"
      width="80%"
      :before-close="handleLoginHistoryDialogClose"
    >
      <el-table :data="loginHistory" stripe>
        <el-table-column prop="login_time" label="登录时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.login_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="150" />
        <el-table-column prop="device" label="设备信息" />
        <el-table-column prop="location" label="登录地点" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules, UploadProps } from 'element-plus'
import {
  Camera,
  ChatDotRound,
  Message,
  Timer,
  Calendar
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const authStore = useAuthStore()

// 数据状态
const editingProfile = ref(false)
const savingProfile = ref(false)
const savingPreferences = ref(false)
const changingPassword = ref(false)
const passwordDialogVisible = ref(false)
const loginHistoryDialogVisible = ref(false)

// 表单引用
const profileFormRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()

// 用户信息
const userInfo = reactive({
  id: '',
  username: '',
  nickname: '',
  email: '',
  phone: '',
  bio: '',
  avatar_url: '',
  two_factor_enabled: false,
  created_at: '',
  last_login: ''
})

// 原始用户信息（用于取消编辑时恢复）
const originalUserInfo = ref<any>({})

// 偏好设置
const preferences = reactive({
  theme: 'light',
  language: 'zh-CN',
  email_notifications: ['system', 'security'],
  sound_enabled: true
})

// 修改密码表单
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 用户统计
const userStats = reactive({
  total_conversations: 25,
  total_messages: 1247,
  total_time: '45小时',
  days_active: 28
})

// 登录记录
const loginHistory = ref([
  {
    login_time: '2024-01-10T14:30:00Z',
    ip_address: '192.168.1.100',
    device: 'Chrome 120.0 / Windows 10',
    location: '北京',
    status: 'success'
  },
  {
    login_time: '2024-01-09T09:15:00Z',
    ip_address: '192.168.1.100',
    device: 'Chrome 120.0 / Windows 10',
    location: '北京',
    status: 'success'
  },
  {
    login_time: '2024-01-08T16:45:00Z',
    ip_address: '10.0.0.50',
    device: 'Safari 17.0 / iOS 17',
    location: '上海',
    status: 'success'
  }
])

// 表单验证规则
const profileRules: FormRules = {
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 2, max: 20, message: '昵称长度为2-20个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

const passwordRules: FormRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: Function) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 头像上传前验证
const beforeAvatarUpload: UploadProps['beforeUpload'] = (rawFile) => {
  if (rawFile.type !== 'image/jpeg' && rawFile.type !== 'image/png') {
    ElMessage.error('头像必须是 JPG 或 PNG 格式!')
    return false
  } else if (rawFile.size / 1024 / 1024 > 2) {
    ElMessage.error('头像大小不能超过 2MB!')
    return false
  }
  return true
}

// 处理头像上传
const handleAvatarUpload = (options: any) => {
  // TODO: 实现头像上传逻辑
  const formData = new FormData()
  formData.append('file', options.file)
  
  // 模拟上传成功
  setTimeout(() => {
    const fakeUrl = URL.createObjectURL(options.file)
    userInfo.avatar_url = fakeUrl
    ElMessage.success('头像上传成功')
  }, 1000)
}

// 保存个人资料
const saveProfile = async () => {
  if (!profileFormRef.value) return
  
  try {
    await profileFormRef.value.validate()
    
    savingProfile.value = true
    
    // TODO: 调用API保存个人资料
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    editingProfile.value = false
    ElMessage.success('个人资料更新成功')
    
    // 更新认证store中的用户信息
    authStore.updateUserInfo(userInfo)
  } catch (error) {
    if (error !== false) {
      ElMessage.error('保存失败，请检查表单')
    }
  } finally {
    savingProfile.value = false
  }
}

// 取消编辑
const cancelEdit = () => {
  Object.assign(userInfo, originalUserInfo.value)
  editingProfile.value = false
  profileFormRef.value?.clearValidate()
}

// 显示修改密码对话框
const showChangePasswordDialog = () => {
  passwordForm.currentPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  passwordDialogVisible.value = true
}

// 修改密码
const changePassword = async () => {
  if (!passwordFormRef.value) return
  
  try {
    await passwordFormRef.value.validate()
    
    changingPassword.value = true
    
    // TODO: 调用API修改密码
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    passwordDialogVisible.value = false
    ElMessage.success('密码修改成功，请重新登录')
    
    // 可以选择是否强制重新登录
    // authStore.logout()
  } catch (error) {
    if (error !== false) {
      ElMessage.error('密码修改失败')
    }
  } finally {
    changingPassword.value = false
  }
}

// 关闭修改密码对话框
const handlePasswordDialogClose = () => {
  passwordDialogVisible.value = false
  passwordFormRef.value?.clearValidate()
}

// 切换两步验证
const toggleTwoFactor = async (enabled: boolean) => {
  try {
    // TODO: 调用API切换两步验证
    await new Promise(resolve => setTimeout(resolve, 500))
    
    ElMessage.success(enabled ? '已开启两步验证' : '已关闭两步验证')
  } catch (error) {
    // 回滚状态
    userInfo.two_factor_enabled = !enabled
    ElMessage.error('设置失败')
  }
}

// 显示登录记录
const showLoginHistory = () => {
  loginHistoryDialogVisible.value = true
}

// 关闭登录记录对话框
const handleLoginHistoryDialogClose = () => {
  loginHistoryDialogVisible.value = false
}

// 保存偏好设置
const savePreferences = async () => {
  try {
    savingPreferences.value = true
    
    // TODO: 调用API保存偏好设置
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('偏好设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingPreferences.value = false
  }
}

// 初始化数据
const initData = () => {
  // 从认证store获取用户信息
  const authUser = authStore.user
  if (authUser) {
    Object.assign(userInfo, {
      id: authUser.id,
      username: authUser.username,
      nickname: authUser.nickname || authUser.username,
      email: authUser.email || '',
      phone: authUser.phone || '',
      bio: authUser.bio || '',
      avatar_url: authUser.avatar_url || '',
      two_factor_enabled: false,
      created_at: authUser.created_at || '',
      last_login: authUser.last_login || ''
    })
    
    // 保存原始数据
    originalUserInfo.value = { ...userInfo }
  }
}

onMounted(() => {
  initData()
})
</script>

<style scoped>
.profile-container {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.profile-card .profile-info {
  display: flex;
  gap: 32px;
}

.avatar-section {
  flex-shrink: 0;
}

.avatar-uploader {
  position: relative;
  cursor: pointer;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.3s;
  color: white;
  font-size: 24px;
}

.avatar-uploader:hover .avatar-overlay {
  opacity: 1;
}

.info-section {
  flex: 1;
}

.security-settings,
.preferences-settings {
  padding: 8px 0;
}

.security-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.security-info h4 {
  margin: 0 0 4px 0;
  color: var(--el-text-color-primary);
}

.security-info p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.stat-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.stat-content {
  text-align: left;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-info {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 20px !important;
  }
  
  .security-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>