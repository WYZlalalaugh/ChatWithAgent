import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 配置进度条
NProgress.configure({ showSpinner: false })

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: {
      title: '登录',
      requiresAuth: false,
    },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: {
          title: '仪表盘',
          icon: 'Dashboard',
        },
      },
      {
        path: '/bots',
        name: 'Bots',
        redirect: '/bots/list',
        meta: {
          title: '机器人管理',
          icon: 'Avatar',
        },
        children: [
          {
            path: '/bots/list',
            name: 'BotsList',
            component: () => import('@/views/bots/List.vue'),
            meta: {
              title: '机器人列表',
            },
          },
          {
            path: '/bots/create',
            name: 'BotsCreate',
            component: () => import('@/views/bots/Create.vue'),
            meta: {
              title: '创建机器人',
            },
          },
          {
            path: '/bots/:id/edit',
            name: 'BotsEdit',
            component: () => import('@/views/bots/Edit.vue'),
            meta: {
              title: '编辑机器人',
            },
          },
          {
            path: '/bots/:id/detail',
            name: 'BotsDetail',
            component: () => import('@/views/bots/Detail.vue'),
            meta: {
              title: '机器人详情',
            },
          },
        ],
      },
      {
        path: '/conversations',
        name: 'Conversations',
        redirect: '/conversations/list',
        meta: {
          title: '对话管理',
          icon: 'ChatLineRound',
        },
        children: [
          {
            path: '/conversations/list',
            name: 'ConversationsList',
            component: () => import('@/views/conversations/List.vue'),
            meta: {
              title: '对话列表',
            },
          },
          {
            path: '/conversations/:id/detail',
            name: 'ConversationsDetail',
            component: () => import('@/views/conversations/Detail.vue'),
            meta: {
              title: '对话详情',
            },
          },
        ],
      },
      {
        path: '/chat/:id?',
        name: 'Chat',
        component: () => import('@/views/Chat.vue'),
        meta: {
          title: '聊天',
          icon: 'ChatDotRound',
        },
      },
      {
        path: '/knowledge',
        name: 'Knowledge',
        redirect: '/knowledge/bases',
        meta: {
          title: '知识库',
          icon: 'Collection',
        },
        children: [
          {
            path: '/knowledge/bases',
            name: 'KnowledgeBases',
            component: () => import('@/views/knowledge/Bases.vue'),
            meta: {
              title: '知识库管理',
            },
          },
          {
            path: '/knowledge/bases/:id/documents',
            name: 'KnowledgeDocuments',
            component: () => import('@/views/knowledge/Documents.vue'),
            meta: {
              title: '文档管理',
            },
          },
        ],
      },
      {
        path: '/plugins',
        name: 'Plugins',
        redirect: '/plugins/installed',
        meta: {
          title: '插件管理',
          icon: 'Connection',
        },
        children: [
          {
            path: '/plugins/installed',
            name: 'PluginsInstalled',
            component: () => import('@/views/plugins/Installed.vue'),
            meta: {
              title: '已安装插件',
            },
          },
          {
            path: '/plugins/marketplace',
            name: 'PluginsMarketplace',
            component: () => import('@/views/plugins/Marketplace.vue'),
            meta: {
              title: '插件市场',
            },
          },
        ],
      },
      {
        path: '/users',
        name: 'Users',
        component: () => import('@/views/users/List.vue'),
        meta: {
          title: '用户管理',
          icon: 'User',
          roles: ['admin'],
        },
      },
      {
        path: '/system',
        name: 'System',
        redirect: '/system/config',
        meta: {
          title: '系统管理',
          icon: 'Setting',
          roles: ['admin'],
        },
        children: [
          {
            path: '/system/config',
            name: 'SystemConfig',
            component: () => import('@/views/system/Config.vue'),
            meta: {
              title: '系统配置',
            },
          },
          {
            path: '/system/logs',
            name: 'SystemLogs',
            component: () => import('@/views/system/Logs.vue'),
            meta: {
              title: '系统日志',
            },
          },
          {
            path: '/system/monitoring',
            name: 'SystemMonitoring',
            component: () => import('@/views/system/Monitoring.vue'),
            meta: {
              title: '系统监控',
            },
          },
        ],
      },
      {
        path: '/profile',
        name: 'Profile',
        component: () => import('@/views/profile/Index.vue'),
        meta: {
          title: '个人中心',
          icon: 'UserFilled',
        },
      },
    ],
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: {
      title: '页面不存在',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  },
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  NProgress.start()

  // 暂时禁用认证检查，直接通过（等后端 API 完善后再启用）
  next()
  return

  // 以下代码暂时注释
  /*
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth) {
    if (!authStore.token) {
      next('/login')
      return
    }

    // 检查用户信息
    if (!authStore.user) {
      try {
        await authStore.fetchUserInfo()
      } catch {
        authStore.logout()
        next('/login')
        return
      }
    }

    // 检查角色权限
    const requiredRoles = to.meta.roles as string[]
    if (requiredRoles && requiredRoles.length > 0) {
      if (!authStore.user || !requiredRoles.includes(authStore.user.role)) {
        next('/404')
        return
      }
    }
  } else {
    // 已登录用户访问登录页面时重定向到首页
    if (to.path === '/login' && authStore.token) {
      next('/')
      return
    }
  }

  next()
  */
})

router.afterEach((to) => {
  NProgress.done()
  
  // 设置页面标题
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - ChatAgent`
  } else {
    document.title = 'ChatAgent - 智能聊天机器人管理平台'
  }
})

export default router