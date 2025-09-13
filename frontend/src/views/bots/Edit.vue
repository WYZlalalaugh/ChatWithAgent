<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">编辑机器人</h1>
      <div class="page-actions">
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">
          保存修改
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
              disabled
            >
              <el-option
                v-for="platform in platforms"
                :key="platform.value"
                :label="platform.label"
                :value="platform.value"
              />
            </el-select>
          </el-form-item>
        </div>

        <!-- AI 模型配置 -->
        <div class="form-section">
          <h3 class="form-section-title">AI 模型配置</h3>
          
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
          
          <el-form-item label="状态">
            <el-switch
              v-model="formData.is_active"
              active-text="启用"
              inactive-text="禁用"
            />
          </el-form-item>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules, UploadProps } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()
const loading = ref(false)

// 机器人ID
const botId = route.params.id as string

// 表单数据
const formData = reactive({
  name: '',
  description: '',
  avatar_url: '',
  platform_type: '',
  llm_config: {
    system_prompt: '',
    temperature: 0.7,
    max_tokens: 2000
  },
  enable_knowledge: false,
  knowledge_base_ids: [],
  is_active: true
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入机器人名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度为2-50个字符', trigger: 'blur' }
  ]
}

// 平台选项
const platforms = ref([
  { label: 'QQ', value: 'qq' },
  { label: '微信', value: 'wechat' },
  { label: '飞书', value: 'feishu' },
  { label: '钉钉', value: 'dingtalk' },
  { label: 'Telegram', value: 'telegram' }
])

// 知识库列表（模拟数据）
const knowledgeBases = ref([
  { id: '1', name: '产品手册' },
  { id: '2', name: '常见问题' },
  { id: '3', name: '技术文档' }
])

// 处理知识库开关
const handleKnowledgeToggle = (enabled: boolean) => {
  if (!enabled) {
    formData.knowledge_base_ids = []
  }
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
  const formDataObj = new FormData()
  formDataObj.append('file', options.file)
  
  // 模拟上传成功
  setTimeout(() => {
    const fakeUrl = URL.createObjectURL(options.file)
    formData.avatar_url = fakeUrl
    ElMessage.success('头像上传成功')
  }, 1000)
}

// 加载机器人信息
const loadBotInfo = async () => {
  try {
    loading.value = true
    // TODO: 调用API获取机器人信息
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟数据
    Object.assign(formData, {
      name: '测试机器人',
      description: '这是一个测试机器人',
      platform_type: 'qq',
      llm_config: {
        system_prompt: '你是一个有用的AI助手',
        temperature: 0.7,
        max_tokens: 2000
      },
      enable_knowledge: false,
      knowledge_base_ids: [],
      is_active: true
    })
  } catch (error) {
    ElMessage.error('加载机器人信息失败')
  } finally {
    loading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    loading.value = true
    
    // TODO: 调用API更新机器人
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    ElMessage.success('机器人更新成功')
    router.push('/bots')
    
  } catch (error) {
    if (error !== false) {
      ElMessage.error('更新失败，请检查表单')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBotInfo()
})
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