// 认证相关类型
export interface User {
  id: string
  username: string
  nickname: string
  email: string
  role: 'admin' | 'user' | 'developer'
  avatar_url?: string
  is_active: boolean
  created_at: string
  last_login?: string
}

export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  password: string
  email: string
  nickname?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_info: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}