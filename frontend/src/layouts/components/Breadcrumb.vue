<template>
  <el-breadcrumb separator="/">
    <el-breadcrumb-item
      v-for="(item, index) in breadcrumbItems"
      :key="item.path"
      :to="index === breadcrumbItems.length - 1 ? undefined : item.path"
    >
      <el-icon v-if="item.icon" class="breadcrumb-icon">
        <component :is="item.icon" />
      </el-icon>
      {{ item.title }}
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

interface BreadcrumbItem {
  path: string
  title: string
  icon?: string
}

const breadcrumbItems = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  const items: BreadcrumbItem[] = []
  
  // 添加首页
  if (route.path !== '/dashboard') {
    items.push({
      path: '/dashboard',
      title: '首页',
      icon: 'House'
    })
  }
  
  // 添加匹配的路由
  matched.forEach(item => {
    if (item.path !== '/' && item.meta?.title) {
      items.push({
        path: item.path,
        title: item.meta.title as string,
        icon: item.meta.icon as string
      })
    }
  })
  
  return items
})
</script>

<style scoped>
.breadcrumb-icon {
  margin-right: 4px;
  font-size: 14px;
}

:deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--el-text-color-regular);
  cursor: default;
}

:deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner:hover) {
  color: var(--el-text-color-regular);
}
</style>