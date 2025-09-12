<template>
  <div class="app-container">
    <!-- 侧边栏 -->
    <aside
      :class="[
        'sidebar',
        { 'sidebar-collapsed': isCollapsed }
      ]"
    >
      <div class="sidebar-header">
        <div class="logo">
          <img v-if="!isCollapsed" src="/logo.png" alt="ChatAgent" class="logo-image" />
          <span v-if="!isCollapsed" class="logo-text">ChatAgent</span>
          <img v-else src="/logo-mini.png" alt="CA" class="logo-mini" />
        </div>
      </div>
      
      <div class="sidebar-content">
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapsed"
          :unique-opened="true"
          router
          background-color="var(--el-menu-bg-color)"
          text-color="var(--el-menu-text-color)"
          active-text-color="var(--el-color-primary)"
        >
          <menu-item 
            v-for="route in menuRoutes" 
            :key="route.path" 
            :route="route"
          />
        </el-menu>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 顶部导航 -->
      <header class="header">
        <div class="header-left">
          <el-button
            :icon="isCollapsed ? Expand : Fold"
            text
            @click="toggleSidebar"
          />
          <breadcrumb />
        </div>
        
        <div class="header-right">
          <header-actions />
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="route.path" />
            </keep-alive>
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Expand, Fold } from '@element-plus/icons-vue'
import MenuItem from './components/MenuItem.vue'
import Breadcrumb from './components/Breadcrumb.vue'
import HeaderActions from './components/HeaderActions.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 侧边栏状态
const isCollapsed = ref(false)

// 当前激活的菜单
const activeMenu = computed(() => {
  const { path } = route
  return path
})

// 缓存的视图
const cachedViews = ref<string[]>([])

// 菜单路由
const menuRoutes = computed(() => {
  const routes = router.getRoutes()
  return routes
    .filter(route => {
      // 过滤掉不需要在菜单中显示的路由
      return route.meta?.title && !route.meta?.hidden && route.path !== '/login'
    })
    .filter(route => {
      // 角色权限过滤
      const requiredRoles = route.meta?.roles as string[]
      if (requiredRoles && requiredRoles.length > 0) {
        return authStore.user && requiredRoles.includes(authStore.user.role)
      }
      return true
    })
    .sort((a, b) => {
      // 按照order排序，没有order的放最后
      const orderA = (a.meta?.order as number) || 999
      const orderB = (b.meta?.order as number) || 999
      return orderA - orderB
    })
})

// 切换侧边栏
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  background-color: var(--el-bg-color-page);
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  transition: width 0.3s ease;
  display: flex;
  flex-direction: column;
}

.sidebar-collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color);
  padding: 0 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-image {
  height: 32px;
  width: auto;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.logo-mini {
  height: 32px;
  width: 32px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: var(--header-height);
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-content {
  flex: 1;
  overflow-y: auto;
  background: var(--el-bg-color-page);
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
    height: 100vh;
    transform: translateX(-100%);
  }
  
  .sidebar:not(.sidebar-collapsed) {
    transform: translateX(0);
  }
  
  .main-content {
    margin-left: 0;
  }
}
</style>