import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginForm, RegisterForm } from '@/types/auth'
import { authApi } from '@/api/auth'
import { removeToken, setToken, getToken } from '@/utils/auth'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref<string>('')
  const user = ref<User | null>(null)
  const loading = ref(false)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const userName = computed(() => user.value?.nickname || user.value?.username || '')
  const userAvatar = computed(() => user.value?.avatar_url || '')

  // 初始化认证状态
  const initAuth = () => {
    const savedToken = getToken()
    if (savedToken) {
      token.value = savedToken
    }
  }

  // 登录
  const login = async (loginForm: LoginForm) => {
    try {
      loading.value = true
      const response = await authApi.login(loginForm)
      
      token.value = response.access_token
      user.value = response.user_info
      
      setToken(response.access_token)
      
      ElMessage.success('登录成功')
      return response
    } catch (error: any) {
      ElMessage.error(error.message || '登录失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 注册
  const register = async (registerForm: RegisterForm) => {
    try {
      loading.value = true
      const response = await authApi.register(registerForm)
      
      ElMessage.success('注册成功，请登录')
      return response
    } catch (error: any) {
      ElMessage.error(error.message || '注册失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 登出
  const logout = async () => {
    try {
      if (token.value) {
        await authApi.logout()
      }
    } catch (error) {
      console.warn('登出请求失败:', error)
    } finally {
      token.value = ''
      user.value = null
      removeToken()
      ElMessage.success('已登出')
    }
  }

  // 获取用户信息
  const fetchUserInfo = async () => {
    try {
      const userInfo = await authApi.getUserInfo()
      user.value = userInfo
      return userInfo
    } catch (error: any) {
      ElMessage.error('获取用户信息失败')
      throw error
    }
  }

  // 修改密码
  const changePassword = async (oldPassword: string, newPassword: string) => {
    try {
      loading.value = true
      await authApi.changePassword(oldPassword, newPassword)
      
      ElMessage.success('密码修改成功，请重新登录')
      await logout()
    } catch (error: any) {
      ElMessage.error(error.message || '密码修改失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 刷新令牌
  const refreshToken = async (refreshToken: string) => {
    try {
      const response = await authApi.refreshToken(refreshToken)
      
      token.value = response.access_token
      user.value = response.user_info
      
      setToken(response.access_token)
      return response
    } catch (error: any) {
      ElMessage.error('令牌刷新失败，请重新登录')
      await logout()
      throw error
    }
  }

  // 更新用户信息
  const updateUserInfo = (userInfo: Partial<User>) => {
    if (user.value) {
      user.value = { ...user.value, ...userInfo }
    }
  }

  return {
    // 状态
    token,
    user,
    loading,
    
    // 计算属性
    isLoggedIn,
    isAdmin,
    userName,
    userAvatar,
    
    // 方法
    initAuth,
    login,
    register,
    logout,
    fetchUserInfo,
    changePassword,
    refreshToken,
    updateUserInfo,
  }
})