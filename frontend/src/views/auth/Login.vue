<template>
  <div class="login-container">
    <div class="login-content">
      <!-- 左侧说明 -->
      <div class="login-info">
        <div class="info-content">
          <h1 class="info-title">ChatAgent</h1>
          <p class="info-subtitle">开源大语言模型原生即时通信机器人开发平台</p>
          
          <div class="features">
            <div class="feature-item">
              <el-icon class="feature-icon"><Robot /></el-icon>
              <div class="feature-text">
                <h3>智能机器人</h3>
                <p>支持多平台、多模态的智能聊天机器人</p>
              </div>
            </div>
            
            <div class="feature-item">
              <el-icon class="feature-icon"><Connection /></el-icon>
              <div class="feature-text">
                <h3>插件生态</h3>
                <p>丰富的插件系统，轻松扩展功能</p>
              </div>
            </div>
            
            <div class="feature-item">
              <el-icon class="feature-icon"><Collection /></el-icon>
              <div class="feature-text">
                <h3>知识管理</h3>
                <p>强大的RAG知识库系统</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 右侧登录表单 -->
      <div class="login-form-container">
        <div class="login-form">
          <div class="form-header">
            <h2>{{ isLoginMode ? '登录' : '注册' }}</h2>
            <p>{{ isLoginMode ? '欢迎回来' : '创建您的账户' }}</p>
          </div>
          
          <el-form
            ref="formRef"
            :model="formData"
            :rules="formRules"
            size="large"
            @submit.prevent="handleSubmit"
          >
            <el-form-item prop="username">
              <el-input
                v-model="formData.username"
                placeholder="用户名"
                :prefix-icon="User"
                clearable
              />
            </el-form-item>
            
            <el-form-item v-if="!isLoginMode" prop="email">
              <el-input
                v-model="formData.email"
                placeholder="邮箱地址"
                :prefix-icon="Message"
                clearable
              />
            </el-form-item>
            
            <el-form-item v-if="!isLoginMode" prop="nickname">
              <el-input
                v-model="formData.nickname"
                placeholder="昵称（可选）"
                :prefix-icon="UserFilled"
                clearable
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input
                v-model="formData.password"
                type="password"
                placeholder="密码"
                :prefix-icon="Lock"
                show-password
                clearable
              />
            </el-form-item>
            
            <el-form-item v-if="!isLoginMode" prop="confirmPassword">
              <el-input
                v-model="formData.confirmPassword"
                type="password"
                placeholder="确认密码"
                :prefix-icon="Lock"
                show-password
                clearable
              />
            </el-form-item>
            
            <el-form-item v-if="isLoginMode">
              <div class="form-options">
                <el-checkbox v-model="rememberMe">记住我</el-checkbox>
                <el-button type="primary" text @click="handleForgotPassword">
                  忘记密码？
                </el-button>
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="authStore.loading"
                @click="handleSubmit"
                style="width: 100%"
              >
                {{ isLoginMode ? '登录' : '注册' }}
              </el-button>
            </el-form-item>
          </el-form>
          
          <div class="form-footer">
            <span>{{ isLoginMode ? '还没有账户？' : '已有账户？' }}</span>
            <el-button type="primary" text @click="toggleMode">
              {{ isLoginMode ? '立即注册' : '立即登录' }}
            </el-button>
          </div>
          
          <!-- 演示账户 -->
          <div class="demo-accounts">
            <el-divider>演示账户</el-divider>
            <div class="demo-buttons">
              <el-button @click="loginAsDemo('admin')" size="small">
                管理员演示
              </el-button>
              <el-button @click="loginAsDemo('user')" size="small">
                普通用户演示
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  User,
  Lock,
  Message,
  UserFilled,
  Robot,
  Connection,
  Collection
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { LoginForm, RegisterForm } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()

// 表单引用
const formRef = ref<FormInstance>()

// 模式切换
const isLoginMode = ref(true)
const rememberMe = ref(false)

// 表单数据
const formData = reactive({
  username: '',
  email: '',
  nickname: '',
  password: '',
  confirmPassword: ''
})

// 表单验证规则
const formRules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' },
    { 
      pattern: /^[a-zA-Z0-9_]+$/, 
      message: '用户名只能包含字母、数字和下划线', 
      trigger: 'blur' 
    }
  ],
  email: isLoginMode.value ? [] : [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ],
  confirmPassword: isLoginMode.value ? [] : [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== formData.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}))

// 切换登录/注册模式
const toggleMode = () => {
  isLoginMode.value = !isLoginMode.value
  resetForm()
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    username: '',
    email: '',
    nickname: '',
    password: '',
    confirmPassword: ''
  })
  formRef.value?.clearValidate()
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (isLoginMode.value) {
      await handleLogin()
    } else {
      await handleRegister()
    }
  } catch (error) {
    console.error('Form validation failed:', error)
  }
}

// 处理登录
const handleLogin = async () => {
  try {
    const loginData: LoginForm = {
      username: formData.username,
      password: formData.password
    }
    
    await authStore.login(loginData)
    
    // 登录成功，跳转到首页
    router.push('/')
  } catch (error) {
    console.error('Login failed:', error)
  }
}

// 处理注册
const handleRegister = async () => {
  try {
    const registerData: RegisterForm = {
      username: formData.username,
      email: formData.email,
      password: formData.password,
      nickname: formData.nickname || undefined
    }
    
    await authStore.register(registerData)
    
    // 注册成功，切换到登录模式
    isLoginMode.value = true
    formData.email = ''
    formData.nickname = ''
    formData.password = ''
    formData.confirmPassword = ''
  } catch (error) {
    console.error('Register failed:', error)
  }
}

// 忘记密码
const handleForgotPassword = async () => {
  try {
    const { value: email } = await ElMessageBox.prompt(
      '请输入您的邮箱地址，我们将发送重置密码的链接',
      '忘记密码',
      {
        confirmButtonText: '发送',
        cancelButtonText: '取消',
        inputPlaceholder: '邮箱地址',
        inputType: 'email'
      }
    )
    
    if (email) {
      // TODO: 调用忘记密码API
      ElMessage.success('重置密码链接已发送到您的邮箱')
    }
  } catch {
    // 用户取消
  }
}

// 演示账户登录
const loginAsDemo = async (role: 'admin' | 'user') => {
  const demoAccounts = {
    admin: { username: 'admin', password: 'admin123' },
    user: { username: 'demo', password: 'demo123' }
  }
  
  try {
    await authStore.login(demoAccounts[role])
    router.push('/')
  } catch (error) {
    ElMessage.error('演示账户登录失败，请使用正常注册流程')
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-content {
  display: flex;
  max-width: 1000px;
  width: 100%;
  min-height: 600px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.login-info {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 60px 40px;
  display: flex;
  align-items: center;
}

.info-content {
  width: 100%;
}

.info-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
  background: linear-gradient(45deg, #fff, #e0e7ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.info-subtitle {
  font-size: 18px;
  margin-bottom: 40px;
  opacity: 0.9;
  line-height: 1.5;
}

.features {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.feature-icon {
  font-size: 24px;
  margin-top: 4px;
  opacity: 0.9;
}

.feature-text h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.feature-text p {
  font-size: 14px;
  opacity: 0.8;
  line-height: 1.4;
}

.login-form-container {
  flex: 1;
  padding: 60px 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-form {
  width: 100%;
  max-width: 380px;
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.form-header p {
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.demo-accounts {
  margin-top: 32px;
}

.demo-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

/* 响应式 */
@media (max-width: 768px) {
  .login-content {
    flex-direction: column;
    max-width: 400px;
  }
  
  .login-info {
    padding: 40px 30px 30px;
  }
  
  .info-title {
    font-size: 28px;
  }
  
  .info-subtitle {
    font-size: 16px;
  }
  
  .login-form-container {
    padding: 30px;
  }
  
  .features {
    display: none;
  }
}

@media (max-width: 480px) {
  .login-container {
    padding: 10px;
  }
  
  .login-info {
    padding: 30px 20px 20px;
  }
  
  .login-form-container {
    padding: 20px;
  }
}
</style>