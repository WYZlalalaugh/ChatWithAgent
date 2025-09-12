<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { provide } from 'vue'
import { useAuthStore } from '@/stores/auth'

// 初始化认证状态
const authStore = useAuthStore()
authStore.initAuth()

// 提供全局配置
provide('$ELEMENT', {
  size: 'default',
  zIndex: 3000,
})
</script>

<style>
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--el-text-color-primary);
  height: 100vh;
  width: 100vw;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  overflow: hidden;
}

.el-loading-mask {
  background-color: rgba(255, 255, 255, 0.8);
}

.dark .el-loading-mask {
  background-color: rgba(0, 0, 0, 0.8);
}
</style>