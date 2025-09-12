<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">创建机器人</h1>
      <div class="page-actions">
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">
          创建机器人
        </el-button>
      </div>
    </div>

    <div class="form-container">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        size="default"
      >
        <!-- 基本信息 -->
        <div class="form-section">
          <h3 class="form-section-title">基本信息</h3>
          
          <el-form-item label="机器人名称" prop="name">
            <el-input
              v-model="formData.name"
              placeholder="请输入机器人名称"
              maxlength="50"
              show-word-limit
            />
          </el-form-item>
          
          <el-form-item label="描述" prop="description">
            <el-input
              v-model="formData.description"
              type="textarea"
              placeholder="请输入机器人描述（可选）"
              :rows="3"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>
          
          <el-form-item label="头像">
            <div class="avatar-upload">
              <el-upload
                class="avatar-uploader"
                action="#"
                :show-file-list="false"
                :before-upload="beforeAvatarUpload"
                :http-request="handleAvatarUpload"
              >
                <img v-if="formData.avatar_url" :src="formData.avatar_url" class="avatar" />
                <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
              </el-upload>
              <div class="avatar-tips">
                <p>建议尺寸：128x128px</p>
                <p>支持 JPG、PNG 格式，文件大小不超过 2MB</p>
              </div>
            </div>
          </el-form-item>
        </div>

        <!-- 平台配置 -->
        <div class="form-section">
          <h3 class="form-section-title">平台配置</h3>
          
          <el-form-item label="平台类型" prop="platform_type">
            <el-select
              v-model="formData.platform_type"
              placeholder="请选择平台类型"
              @change="handlePlatformChange"
            >
              <el-option
                v-for="platform in platforms"
                :key="platform.value"
                :label="platform.label"
                :value="platform.value"
              >
                <div class="platform-option">
                  <el-icon class="platform-icon">
                    <component :is="platform.icon" />
                  </el-icon>
                  <span>{{ platform.label }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <!-- 动态平台配置 -->
          <template v-if="formData.platform_type">
            <component
              :is="getPlatformConfigComponent(formData.platform_type)"
              v-model="formData.platform_config"
              @validate="handlePlatformValidation"
            />
          </template>
        </div>

        <!-- AI 模型配置 -->
        <div class="form-section">
          <h3 class="form-section-title">AI 模型配置</h3>
          
          <el-form-item label="模型提供商" prop="llm_provider">
            <el-select
              v-model="formData.llm_config.provider"
              placeholder="请选择模型提供商"
              @change="handleProviderChange"
            >
              <el-option
                v-for="provider in providers"
                :key="provider.value"
                :label="provider.label"
                :value="provider.value"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="模型" prop="llm_model">
            <el-select
              v-model="formData.llm_config.model"
              placeholder="请选择模型"
              :disabled="!formData.llm_config.provider"
            >
              <el-option
                v-for="model in availableModels"
                :key="model.value"
                :label="model.label"
                :value="model.value"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="系统提示词">
            <el-input
              v-model="formData.llm_config.system_prompt"
              type="textarea"
              placeholder="请输入系统提示词，用于定义机器人的角色和行为..."
              :rows="4"
              maxlength="1000"
              show-word-limit
            />
          </el-form-item>
          
          <el-form-item label="温度">
            <el-slider
              v-model="formData.llm_config.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              show-input
              :input-size="'small'"
            />
            <div class="param-description">
              控制回复的随机性。值越高，回复越有创意；值越低，回复越确定。
            </div>
          </el-form-item>
          
          <el-form-item label="最大令牌数">
            <el-input-number
              v-model="formData.llm_config.max_tokens"
              :min="1"
              :max="4000"
              :step="100"
              style="width: 200px;"
            />
            <div class="param-description">
              控制单次回复的最大长度。
            </div>
          </el-form-item>
        </div>

        <!-- 高级设置 -->
        <div class="form-section">
          <h3 class="form-section-title">高级设置</h3>
          
          <el-form-item label="启用知识库">
            <el-switch
              v-model="formData.enable_knowledge"
              @change="handleKnowledgeToggle"
            />
          </el-form-item>
          
          <template v-if="formData.enable_knowledge">
            <el-form-item label="关联知识库">
              <el-select
                v-model="formData.knowledge_base_ids"
                multiple
                placeholder="请选择要关联的知识库"
                style="width: 100%;"
              >
                <el-option
                  v-for="kb in knowledgeBases"
                  :key="kb.id"
                  :label="kb.name"
                  :value="kb.id"
                />
              </el-select>
            </el-form-item>
          </template>
          
          <el-form-item label="启用插件">
            <el-switch
              v-model="formData.enable_plugins"
              @change="handlePluginsToggle"
            />
          </el-form-item>
          
          <template v-if="formData.enable_plugins">
            <el-form-item label="选择插件">
              <el-select
                v-model="formData.plugin_ids"
                multiple
                placeholder="请选择要启用的插件"
                style="width: 100%;"
              >
                <el-option
                  v-for="plugin in availablePlugins"
                  :key="plugin.id"
                  :label="plugin.name"
                  :value="plugin.id"
                />
              </el-select>
            </el-form-item>
          </template>
          
          <el-form-item label="自动启动">
            <el-switch v-model="formData.auto_start" />
            <div class="param-description">
              创建后自动启动机器人。
            </div>
          </el-form-item>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules, UploadProps } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// 动态导入平台配置组件
const QQConfig = defineAsyncComponent(() => import('./components/QQConfig.vue'))
const WeChatConfig = defineAsyncComponent(() => import('./components/WeChatConfig.vue'))
const FeishuConfig = defineAsyncComponent(() => import('./components/FeishuConfig.vue'))
const DingtalkConfig = defineAsyncComponent(() => import('./components/DingtalkConfig.vue'))

const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()
const loading = ref(false)

// 表单数据
const formData = reactive({
  name: '',
  description: '',
  avatar_url: '',
  platform_type: '',
  platform_config: {},
  llm_config: {
    provider: 'openai',
    model: 'gpt-3.5-turbo',
    system_prompt: '你是一个有用、无害、诚实的AI助手。请用友好、专业的语气回答用户的问题。',
    temperature: 0.7,
    max_tokens: 2000
  },
  enable_knowledge: false,
  knowledge_base_ids: [],
  enable_plugins: false,
  plugin_ids: [],
  auto_start: true
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入机器人名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度为2-50个字符', trigger: 'blur' }
  ],
  platform_type: [
    { required: true, message: '请选择平台类型', trigger: 'change' }
  ],
  llm_provider: [
    { required: true, message: '请选择模型提供商', trigger: 'change' }
  ],
  llm_model: [
    { required: true, message: '请选择模型', trigger: 'change' }
  ]
}

// 平台选项
const platforms = ref([
  { label: 'QQ', value: 'qq', icon: 'ChatDotRound' },
  { label: '微信', value: 'wechat', icon: 'ChatLineSquare' },
  { label: '飞书', value: 'feishu', icon: 'Message' },
  { label: '钉钉', value: 'dingtalk', icon: 'ChatLineRound' },
  { label: 'Telegram', value: 'telegram', icon: 'ChatDotSquare' }
])

// 模型提供商
const providers = ref([
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Azure OpenAI', value: 'azure' },
  { label: '本地模型', value: 'local' }
])

// 可用模型
const availableModels = computed(() => {
  const modelMap = {
    openai: [
      { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
      { label: 'GPT-4', value: 'gpt-4' },
      { label: 'GPT-4 Turbo', value: 'gpt-4-turbo-preview' }
    ],
    anthropic: [
      { label: 'Claude 3 Haiku', value: 'claude-3-haiku-20240307' },
      { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet-20240229' },
      { label: 'Claude 3 Opus', value: 'claude-3-opus-20240229' }
    ],
    azure: [
      { label: 'GPT-3.5 Turbo', value: 'gpt-35-turbo' },
      { label: 'GPT-4', value: 'gpt-4' }
    ],
    local: [
      { label: 'LLaMA 2', value: 'llama2' },
      { label: 'ChatGLM', value: 'chatglm' }
    ]
  }
  
  return modelMap[formData.llm_config.provider] || []
})

// 知识库列表（模拟数据）
const knowledgeBases = ref([
  { id: '1', name: '产品手册' },
  { id: '2', name: '常见问题' },
  { id: '3', name: '技术文档' }
])

// 可用插件（模拟数据）
const availablePlugins = ref([
  { id: '1', name: '天气查询' },
  { id: '2', name: '快递查询' },
  { id: '3', name: '翻译助手' }
])

// 获取平台配置组件
const getPlatformConfigComponent = (platform: string) => {
  const componentMap = {
    qq: QQConfig,
    wechat: WeChatConfig,
    feishu: FeishuConfig,
    dingtalk: DingtalkConfig
  }
  return componentMap[platform] || 'div'
}

// 处理平台变化
const handlePlatformChange = (platform: string) => {
  formData.platform_config = {}
}

// 处理提供商变化
const handleProviderChange = (provider: string) => {
  formData.llm_config.model = ''
}

// 处理知识库开关
const handleKnowledgeToggle = (enabled: boolean) => {
  if (!enabled) {
    formData.knowledge_base_ids = []
  }
}

// 处理插件开关
const handlePluginsToggle = (enabled: boolean) => {
  if (!enabled) {
    formData.plugin_ids = []
  }
}

// 处理平台配置验证
const handlePlatformValidation = (isValid: boolean) => {
  // 平台配置验证回调
}

// 头像上传前验证
const beforeAvatarUpload: UploadProps['beforeUpload'] = (rawFile) => {
  if (rawFile.type !== 'image/jpeg' && rawFile.type !== 'image/png') {
    ElMessage.error('头像必须是 JPG 或 PNG 格式!')
    return false
  } else if (rawFile.size / 1024 / 1024 > 2) {
    ElMessage.error('头像大小不能超过 2MB!')
    return false
  }
  return true
}

// 处理头像上传
const handleAvatarUpload = (options: any) => {
  // TODO: 实现头像上传逻辑
  const formData = new FormData()
  formData.append('file', options.file)
  
  // 模拟上传成功
  setTimeout(() => {
    const fakeUrl = URL.createObjectURL(options.file)
    formData.avatar_url = fakeUrl
    ElMessage.success('头像上传成功')
  }, 1000)
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    loading.value = true
    
    // TODO: 调用API创建机器人
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    ElMessage.success('机器人创建成功')
    router.push('/bots')
    
  } catch (error) {
    if (error !== false) { // 验证失败时error为false
      ElMessage.error('创建失败，请检查表单')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.avatar-upload {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.avatar-uploader {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}

.avatar-uploader:hover {
  border-color: var(--el-color-primary);
}

.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar {
  width: 80px;
  height: 80px;
  display: block;
  object-fit: cover;
}

.avatar-tips {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.platform-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-icon {
  font-size: 16px;
}

.param-description {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}

@media (max-width: 768px) {
  .form-container {
    padding: 16px;
  }
  
  :deep(.el-form-item__label) {
    width: 100px !important;
  }
}
</style>