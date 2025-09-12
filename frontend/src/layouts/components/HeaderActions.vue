<template>
  <div class="header-actions">
    <!-- 主题切换 -->
    <el-tooltip content="切换主题" placement="bottom">
      <el-button
        :icon="isDark ? Sunny : Moon"
        circle
        text
        @click="toggleTheme"
      />
    </el-tooltip>
    
    <!-- 全屏切换 -->
    <el-tooltip content="全屏" placement="bottom">
      <el-button
        :icon="FullScreen"
        circle
        text
        @click="toggleFullscreen"
      />
    </el-tooltip>
    
    <!-- 通知 -->
    <el-popover
      placement="bottom"
      :width="320"
      trigger="click"
    >
      <template #reference>
        <el-badge :value="unreadCount" :hidden="unreadCount === 0">
          <el-button
            :icon="Bell"
            circle
            text
          />
        </el-badge>
      </template>
      
      <div class="notifications">
        <div class="notifications-header">
          <span>通知中心</span>
          <el-button text size="small" @click="clearAll">全部已读</el-button>
        </div>
        
        <div v-if="notifications.length === 0" class="no-notifications">
          <el-empty description="暂无通知" />
        </div>
        
        <div v-else class="notifications-list">
          <div
            v-for="notification in notifications"
            :key="notification.id"
            class="notification-item"
            :class="{ 'unread': !notification.read }"
            @click="markAsRead(notification.id)"
          >
            <div class="notification-content">
              <div class="notification-title">{{ notification.title }}</div>
              <div class="notification-message">{{ notification.message }}</div>
              <div class="notification-time">{{ formatTime(notification.created_at) }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-popover>
    
    <!-- 用户菜单 -->
    <el-dropdown @command="handleUserCommand">
      <div class="user-info">
        <el-avatar
          :src="authStore.userAvatar"
          :size="32"
          class="user-avatar"
        >
          {{ authStore.userName.charAt(0).toUpperCase() }}
        </el-avatar>
        <span class="user-name">{{ authStore.userName }}</span>
        <el-icon class="dropdown-icon">
          <ArrowDown />
        </el-icon>
      </div>
      
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="profile" :icon="User">
            个人中心
          </el-dropdown-item>
          <el-dropdown-item command="settings" :icon="Setting">
            账户设置
          </el-dropdown-item>
          <el-dropdown-item divided command="logout" :icon="SwitchButton">
            退出登录
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Sunny,
  Moon,
  FullScreen,
  Bell,
  User,
  Setting,
  SwitchButton,
  ArrowDown
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const router = useRouter()
const authStore = useAuthStore()

// 主题状态
const isDark = ref(false)

// 通知数据
const notifications = ref([
  {
    id: '1',
    title: '系统通知',
    message: '您的机器人 "客服助手" 已成功启动',
    created_at: '2024-01-10T10:30:00Z',
    read: false
  },
  {
    id: '2',
    title: '警告',
    message: '知识库 "产品手册" 存储空间不足',
    created_at: '2024-01-10T09:15:00Z',
    read: false
  }
])

// 未读通知数量
const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.read).length
})

// 切换主题
const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
}

// 切换全屏
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

// 标记为已读
const markAsRead = (id: string) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification) {
    notification.read = true
  }
}

// 清除所有通知
const clearAll = () => {
  notifications.value.forEach(n => {
    n.read = true
  })
}

// 格式化时间
const formatTime = (time: string) => {
  return dayjs(time).format('MM-DD HH:mm')
}

// 处理用户菜单命令
const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/profile?tab=settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '确认', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        await authStore.logout()
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}
</script>

<style scoped>
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: var(--el-fill-color-light);
}

.user-avatar {
  flex-shrink: 0;
}

.user-name {
  font-size: 14px;
  color: var(--el-text-color-primary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-icon {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  transition: transform 0.3s;
}

.notifications {
  max-height: 400px;
  overflow-y: auto;
}

.notifications-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 8px;
  font-weight: 600;
}

.no-notifications {
  padding: 20px 0;
}

.notifications-list {
  max-height: 300px;
  overflow-y: auto;
}

.notification-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-bottom: 4px;
}

.notification-item:hover {
  background-color: var(--el-fill-color-light);
}

.notification-item.unread {
  background-color: var(--el-color-primary-light-9);
  border-left: 3px solid var(--el-color-primary);
}

.notification-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.notification-message {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.4;
}

.notification-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .user-name {
    display: none;
  }
}
</style>