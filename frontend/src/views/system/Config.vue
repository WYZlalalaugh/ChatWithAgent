<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统配置</h1>
      <div class="page-actions">
        <el-button type="primary" :loading="saving" @click="saveConfig">
          保存配置
        </el-button>
      </div>
    </div>

    <div class="config-container">
      <el-form
        ref="formRef"
        :model="config"
        :rules="formRules"
        label-width="150px"
        size="default"
      >
        <!-- 基本配置 -->
        <el-card class="config-section">
          <template #header>
            <span>基本配置</span>
          </template>
          
          <el-form-item label="系统名称" prop="system_name">
            <el-input v-model="config.system_name" placeholder="请输入系统名称" />
          </el-form-item>
          
          <el-form-item label="系统描述">
            <el-input
              v-model="config.system_description"
              type="textarea"
              :rows="3"
              placeholder="请输入系统描述"
            />
          </el-form-item>
          
          <el-form-item label="系统Logo">
            <el-upload
              class="logo-uploader"
              action="#"
              :show-file-list="false"
              :before-upload="beforeLogoUpload"
              :http-request="handleLogoUpload"
            >
              <img v-if="config.system_logo" :src="config.system_logo" class="logo" />
              <el-icon v-else class="logo-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>
          
          <el-form-item label="时区设置">
            <el-select v-model="config.timezone" placeholder="请选择时区">
              <el-option label="北京时间 (UTC+8)" value="Asia/Shanghai" />
              <el-option label="东京时间 (UTC+9)" value="Asia/Tokyo" />
              <el-option label="伦敦时间 (UTC+0)" value="Europe/London" />
              <el-option label="纽约时间 (UTC-5)" value="America/New_York" />
            </el-select>
          </el-form-item>
        </el-card>

        <!-- AI模型配置 -->
        <el-card class="config-section">
          <template #header>
            <span>AI模型配置</span>
          </template>
          
          <el-form-item label="默认提供商">
            <el-select v-model="config.default_llm_provider" placeholder="请选择默认模型提供商">
              <el-option label="OpenAI" value="openai" />
              <el-option label="Anthropic" value="anthropic" />
              <el-option label="Azure OpenAI" value="azure" />
              <el-option label="本地模型" value="local" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="API密钥" prop="openai_api_key">
            <el-input
              v-model="config.openai_api_key"
              type="password"
              placeholder="请输入OpenAI API密钥"
              show-password
            />
          </el-form-item>
          
          <el-form-item label="默认模型">
            <el-select v-model="config.default_model" placeholder="请选择默认模型">
              <el-option label="GPT-3.5 Turbo" value="gpt-3.5-turbo" />
              <el-option label="GPT-4" value="gpt-4" />
              <el-option label="GPT-4 Turbo" value="gpt-4-turbo" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="最大令牌数">
            <el-input-number v-model="config.max_tokens" :min="100" :max="8000" />
          </el-form-item>
          
          <el-form-item label="温度">
            <el-slider
              v-model="config.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              show-input
            />
          </el-form-item>
        </el-card>

        <!-- 存储配置 -->
        <el-card class="config-section">
          <template #header>
            <span>存储配置</span>
          </template>
          
          <el-form-item label="数据库类型">
            <el-select v-model="config.database_type" placeholder="请选择数据库类型">
              <el-option label="SQLite" value="sqlite" />
              <el-option label="MySQL" value="mysql" />
              <el-option label="PostgreSQL" value="postgresql" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="向量数据库">
            <el-select v-model="config.vector_store_type" placeholder="请选择向量数据库">
              <el-option label="Chroma" value="chroma" />
              <el-option label="FAISS" value="faiss" />
              <el-option label="Qdrant" value="qdrant" />
              <el-option label="Pinecone" value="pinecone" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="文件存储路径">
            <el-input v-model="config.file_storage_path" placeholder="请输入文件存储路径" />
          </el-form-item>
          
          <el-form-item label="最大上传大小(MB)">
            <el-input-number v-model="config.max_upload_size" :min="1" :max="1000" />
          </el-form-item>
        </el-card>

        <!-- 安全配置 -->
        <el-card class="config-section">
          <template #header>
            <span>安全配置</span>
          </template>
          
          <el-form-item label="会话超时(分钟)">
            <el-input-number v-model="config.session_timeout" :min="5" :max="1440" />
          </el-form-item>
          
          <el-form-item label="最大登录尝试次数">
            <el-input-number v-model="config.max_login_attempts" :min="3" :max="10" />
          </el-form-item>
          
          <el-form-item label="启用HTTPS">
            <el-switch v-model="config.enable_https" />
          </el-form-item>
          
          <el-form-item label="允许注册">
            <el-switch v-model="config.allow_registration" />
          </el-form-item>
        </el-card>

        <!-- 通知配置 -->
        <el-card class="config-section">
          <template #header>
            <span>通知配置</span>
          </template>
          
          <el-form-item label="邮件服务器">
            <el-input v-model="config.smtp_server" placeholder="请输入SMTP服务器地址" />
          </el-form-item>
          
          <el-form-item label="邮件端口">
            <el-input-number v-model="config.smtp_port" :min="1" :max="65535" />
          </el-form-item>
          
          <el-form-item label="邮件用户名">
            <el-input v-model="config.smtp_username" placeholder="请输入邮件用户名" />
          </el-form-item>
          
          <el-form-item label="邮件密码">
            <el-input
              v-model="config.smtp_password"
              type="password"
              placeholder="请输入邮件密码"
              show-password
            />
          </el-form-item>
          
          <el-form-item label="启用邮件通知">
            <el-switch v-model="config.enable_email_notification" />
          </el-form-item>
        </el-card>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules, UploadProps } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// 表单引用
const formRef = ref<FormInstance>()
const saving = ref(false)

// 配置数据
const config = reactive({
  // 基本配置
  system_name: 'ChatAgent',
  system_description: '智能对话机器人管理平台',
  system_logo: '',
  timezone: 'Asia/Shanghai',
  
  // AI模型配置
  default_llm_provider: 'openai',
  openai_api_key: '',
  default_model: 'gpt-3.5-turbo',
  max_tokens: 2000,
  temperature: 0.7,
  
  // 存储配置
  database_type: 'sqlite',
  vector_store_type: 'chroma',
  file_storage_path: './storage',
  max_upload_size: 10,
  
  // 安全配置
  session_timeout: 30,
  max_login_attempts: 5,
  enable_https: false,
  allow_registration: true,
  
  // 通知配置
  smtp_server: '',
  smtp_port: 587,
  smtp_username: '',
  smtp_password: '',
  enable_email_notification: false
})

// 表单验证规则
const formRules: FormRules = {
  system_name: [
    { required: true, message: '请输入系统名称', trigger: 'blur' }
  ],
  openai_api_key: [
    { min: 10, message: 'API密钥长度至少10个字符', trigger: 'blur' }
  ]
}

// Logo上传前验证
const beforeLogoUpload: UploadProps['beforeUpload'] = (rawFile) => {
  if (rawFile.type !== 'image/jpeg' && rawFile.type !== 'image/png') {
    ElMessage.error('Logo必须是 JPG 或 PNG 格式!')
    return false
  } else if (rawFile.size / 1024 / 1024 > 2) {
    ElMessage.error('Logo大小不能超过 2MB!')
    return false
  }
  return true
}

// 处理Logo上传
const handleLogoUpload = (options: any) => {
  // TODO: 实现Logo上传逻辑
  const formData = new FormData()
  formData.append('file', options.file)
  
  // 模拟上传成功
  setTimeout(() => {
    const fakeUrl = URL.createObjectURL(options.file)
    config.system_logo = fakeUrl
    ElMessage.success('Logo上传成功')
  }, 1000)
}

// 保存配置
const saveConfig = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    saving.value = true
    
    // TODO: 调用API保存配置
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    ElMessage.success('配置保存成功')
  } catch (error) {
    if (error !== false) {
      ElMessage.error('保存失败，请检查配置')
    }
  } finally {
    saving.value = false
  }
}

// 加载配置
const loadConfig = async () => {
  try {
    // TODO: 调用API加载配置
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟加载配置数据
    ElMessage.success('配置加载完成')
  } catch (error) {
    ElMessage.error('加载配置失败')
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config-container {
  max-width: 800px;
  margin: 0 auto;
}

.config-section {
  margin-bottom: 24px;
}

.logo-uploader {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}

.logo-uploader:hover {
  border-color: var(--el-color-primary);
}

.logo-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo {
  width: 100px;
  height: 100px;
  display: block;
  object-fit: cover;
}

@media (max-width: 768px) {
  .config-container {
    padding: 16px;
  }
  
  :deep(.el-form-item__label) {
    width: 120px !important;
  }
}
</style>