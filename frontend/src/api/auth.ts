import { request } from '@/utils/request'
import type { 
  LoginForm, 
  RegisterForm, 
  LoginResponse, 
  User, 
  PasswordChangeRequest,
  RefreshTokenRequest 
} from '@/types/auth'

export const authApi = {
  // 登录
  login(data: LoginForm): Promise<LoginResponse> {
    return request.post('/v1/auth/login', data)
  },

  // 注册
  register(data: RegisterForm): Promise<{ success: boolean; message: string; user_id: string }> {
    return request.post('/v1/auth/register', data)
  },

  // 登出
  logout(): Promise<{ success: boolean; message: string }> {
    return request.post('/v1/auth/logout')
  },

  // 刷新令牌
  refreshToken(refreshToken: string): Promise<LoginResponse> {
    return request.post('/v1/auth/refresh', { refresh_token: refreshToken })
  },

  // 获取当前用户信息
  getUserInfo(): Promise<User> {
    return request.get('/v1/auth/me')
  },

  // 修改密码
  changePassword(oldPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    return request.post('/v1/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  },

  // 验证令牌
  verifyToken(): Promise<{ valid: boolean; user_id?: string; username?: string; expires_in?: number }> {
    return request.post('/v1/auth/verify-token')
  },
}