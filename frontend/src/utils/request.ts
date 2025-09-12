import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage, ElLoading } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getToken } from '@/utils/auth'
import type { ApiResponse } from '@/types'

// 创建axios实例
const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求loading实例
let loadingInstance: any = null
let requestCount = 0

// 显示loading
const showLoading = () => {
  if (requestCount === 0) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: '加载中...',
      background: 'rgba(0, 0, 0, 0.7)',
    })
  }
  requestCount++
}

// 隐藏loading
const hideLoading = () => {
  requestCount--
  if (requestCount <= 0) {
    requestCount = 0
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
  }
}

// 请求拦截器
service.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // 显示loading
    if (config.loading !== false) {
      showLoading()
    }

    // 添加认证token
    const token = getToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => {
    hideLoading()
    ElMessage.error('请求配置错误')
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    hideLoading()

    const { data } = response
    
    // 如果返回的是文件流，直接返回
    if (response.config.responseType === 'blob') {
      return response
    }

    // 检查业务状态码
    if (data.success === false) {
      ElMessage.error(data.message || data.error || '请求失败')
      return Promise.reject(new Error(data.message || data.error || '请求失败'))
    }

    return data
  },
  (error) => {
    hideLoading()

    // 处理HTTP状态码错误
    const { response } = error
    let message = '网络错误'

    if (response) {
      switch (response.status) {
        case 400:
          message = response.data?.message || '请求参数错误'
          break
        case 401:
          message = '身份认证失败，请重新登录'
          // 清除token并跳转到登录页
          const authStore = useAuthStore()
          authStore.logout()
          window.location.href = '/login'
          break
        case 403:
          message = '权限不足，无法访问该资源'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 429:
          message = '请求过于频繁，请稍后再试'
          break
        case 500:
          message = '服务器内部错误'
          break
        case 502:
          message = '网关错误'
          break
        case 503:
          message = '服务暂时不可用'
          break
        default:
          message = response.data?.message || `请求失败 (${response.status})`
      }
    } else if (error.code === 'ECONNABORTED') {
      message = '请求超时，请检查网络连接'
    } else if (error.message?.includes('Network Error')) {
      message = '网络连接失败，请检查网络'
    }

    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 封装请求方法
export const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.get(url, config)
  },

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.post(url, data, config)
  },

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.put(url, data, config)
  },

  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.patch(url, data, config)
  },

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.delete(url, config)
  },

  upload<T = any>(url: string, file: File, config?: AxiosRequestConfig): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)
    
    return service.post(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
    })
  },

  download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<void> {
    return service.get(url, {
      ...config,
      responseType: 'blob',
    }).then((response: AxiosResponse) => {
      const blob = new Blob([response.data])
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename || 'download'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    })
  },
}

export default service