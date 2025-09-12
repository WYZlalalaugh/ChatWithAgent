import Cookies from 'js-cookie'

const TOKEN_KEY = 'chatagent-token'
const REFRESH_TOKEN_KEY = 'chatagent-refresh-token'
const USER_INFO_KEY = 'chatagent-user-info'

// Token管理
export const getToken = (): string | undefined => {
  return Cookies.get(TOKEN_KEY)
}

export const setToken = (token: string): void => {
  Cookies.set(TOKEN_KEY, token, { expires: 7 }) // 7天过期
}

export const removeToken = (): void => {
  Cookies.remove(TOKEN_KEY)
  Cookies.remove(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_INFO_KEY)
}

// Refresh Token管理
export const getRefreshToken = (): string | undefined => {
  return Cookies.get(REFRESH_TOKEN_KEY)
}

export const setRefreshToken = (token: string): void => {
  Cookies.set(REFRESH_TOKEN_KEY, token, { expires: 30 }) // 30天过期
}

// 用户信息管理
export const getUserInfo = (): any => {
  const userInfo = localStorage.getItem(USER_INFO_KEY)
  return userInfo ? JSON.parse(userInfo) : null
}

export const setUserInfo = (userInfo: any): void => {
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo))
}

export const removeUserInfo = (): void => {
  localStorage.removeItem(USER_INFO_KEY)
}

// 清除所有认证信息
export const clearAuth = (): void => {
  removeToken()
  removeUserInfo()
}