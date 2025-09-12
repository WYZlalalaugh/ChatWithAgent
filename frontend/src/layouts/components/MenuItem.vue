<template>
  <el-sub-menu
    v-if="route.children && route.children.length > 0"
    :index="route.path"
    :key="route.path"
  >
    <template #title>
      <el-icon v-if="route.meta?.icon">
        <component :is="route.meta.icon" />
      </el-icon>
      <span>{{ route.meta?.title }}</span>
    </template>
    
    <menu-item
      v-for="child in route.children"
      :key="child.path"
      :route="child"
    />
  </el-sub-menu>
  
  <el-menu-item
    v-else
    :index="route.path"
    :key="route.path"
  >
    <el-icon v-if="route.meta?.icon">
      <component :is="route.meta.icon" />
    </el-icon>
    <template #title>
      <span>{{ route.meta?.title }}</span>
    </template>
  </el-menu-item>
</template>

<script setup lang="ts">
import type { RouteRecordRaw } from 'vue-router'

interface Props {
  route: RouteRecordRaw
}

defineProps<Props>()
</script>