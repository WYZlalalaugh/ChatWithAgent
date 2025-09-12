<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-illustration">
        <svg
          width="300"
          height="200"
          viewBox="0 0 300 200"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- 404 插图 -->
          <rect x="50" y="60" width="200" height="120" rx="8" fill="#f5f7fa" stroke="#dcdfe6" stroke-width="2"/>
          <circle cx="80" cy="90" r="8" fill="#f56c6c"/>
          <circle cx="100" cy="90" r="8" fill="#e6a23c"/>
          <circle cx="120" cy="90" r="8" fill="#67c23a"/>
          <text x="150" y="130" font-family="Arial, sans-serif" font-size="36" font-weight="bold" fill="#909399">404</text>
          <text x="150" y="155" font-family="Arial, sans-serif" font-size="12" fill="#c0c4cc">页面不存在</text>
        </svg>
      </div>
      
      <div class="error-info">
        <h1 class="error-title">404</h1>
        <h2 class="error-subtitle">页面不存在</h2>
        <p class="error-description">
          抱歉，您访问的页面不存在或已被移除。
          <br>
          请检查网址是否正确，或返回首页继续浏览。
        </p>
        
        <div class="error-actions">
          <el-button type="primary" @click="goHome">
            <el-icon><House /></el-icon>
            返回首页
          </el-button>
          <el-button @click="goBack">
            <el-icon><Back /></el-icon>
            返回上页
          </el-button>
        </div>
        
        <div class="error-suggestions">
          <h3>您可能想要：</h3>
          <ul class="suggestion-list">
            <li>
              <el-button text @click="$router.push('/dashboard')">
                <el-icon><Dashboard /></el-icon>
                查看仪表盘
              </el-button>
            </li>
            <li>
              <el-button text @click="$router.push('/bots')">
                <el-icon><Robot /></el-icon>
                管理机器人
              </el-button>
            </li>
            <li>
              <el-button text @click="$router.push('/conversations')">
                <el-icon><ChatLineRound /></el-icon>
                查看对话
              </el-button>
            </li>
            <li>
              <el-button text @click="$router.push('/knowledge')">
                <el-icon><Collection /></el-icon>
                管理知识库
              </el-button>
            </li>
          </ul>
        </div>
      </div>
    </div>
    
    <div class="error-footer">
      <p>如果问题持续存在，请联系系统管理员</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  House,
  Back,
  Dashboard,
  Robot,
  ChatLineRound,
  Collection
} from '@element-plus/icons-vue'

const router = useRouter()

// 返回首页
const goHome = () => {
  router.push('/')
}

// 返回上一页
const goBack = () => {
  router.back()
}
</script>

<style scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf0 100%);
  padding: 40px 20px;
}

.error-content {
  display: flex;
  align-items: center;
  gap: 60px;
  max-width: 800px;
  margin-bottom: 40px;
}

.error-illustration {
  flex-shrink: 0;
  opacity: 0.8;
}

.error-info {
  flex: 1;
  text-align: left;
}

.error-title {
  font-size: 72px;
  font-weight: 700;
  color: var(--el-color-primary);
  margin: 0 0 16px 0;
  line-height: 1;
}

.error-subtitle {
  font-size: 32px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 24px 0;
}

.error-description {
  font-size: 16px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin-bottom: 32px;
}

.error-actions {
  display: flex;
  gap: 16px;
  margin-bottom: 40px;
}

.error-suggestions {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 24px;
}

.error-suggestions h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 16px;
}

.suggestion-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.suggestion-list li {
  display: flex;
}

.suggestion-list .el-button {
  justify-content: flex-start;
  width: 100%;
  padding: 12px 16px;
  border-radius: 8px;
  transition: all 0.3s;
}

.suggestion-list .el-button:hover {
  background-color: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.suggestion-list .el-button .el-icon {
  margin-right: 8px;
}

.error-footer {
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  opacity: 0.8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .error-content {
    flex-direction: column;
    gap: 40px;
    text-align: center;
  }
  
  .error-info {
    text-align: center;
  }
  
  .error-title {
    font-size: 56px;
  }
  
  .error-subtitle {
    font-size: 24px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .suggestion-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .error-page {
    padding: 20px 16px;
  }
  
  .error-title {
    font-size: 48px;
  }
  
  .error-subtitle {
    font-size: 20px;
  }
  
  .error-description {
    font-size: 14px;
  }
  
  .error-actions .el-button {
    width: 100%;
  }
}

/* 动画效果 */
.error-illustration {
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.error-info {
  animation: fadeInUp 0.8s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>