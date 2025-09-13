<template>
  <div class="feishu-config">
    <el-form-item label="App ID" prop="app_id">
      <el-input
        v-model="modelValue.app_id"
        placeholder="请输入飞书应用的App ID"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="App Secret" prop="app_secret">
      <el-input
        v-model="modelValue.app_secret"
        type="password"
        placeholder="请输入飞书应用的App Secret"
        show-password
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="Verification Token" prop="verification_token">
      <el-input
        v-model="modelValue.verification_token"
        placeholder="请输入事件订阅的Verification Token"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="Encrypt Key">
      <el-input
        v-model="modelValue.encrypt_key"
        placeholder="请输入事件订阅的Encrypt Key（可选）"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="机器人类型">
      <el-radio-group v-model="modelValue.bot_type" @change="handleChange">
        <el-radio label="custom">自建应用</el-radio>
        <el-radio label="marketplace">应用商店应用</el-radio>
      </el-radio-group>
    </el-form-item>
    
    <el-form-item label="权限范围">
      <el-checkbox-group v-model="modelValue.permissions" @change="handleChange">
        <el-checkbox label="im:message">接收和发送消息</el-checkbox>
        <el-checkbox label="im:message:group">群组消息</el-checkbox>
        <el-checkbox label="im:chat">会话管理</el-checkbox>
        <el-checkbox label="contact:user.id">获取用户ID</el-checkbox>
      </el-checkbox-group>
    </el-form-item>
    
    <div class="config-description">
      <p>配置说明：</p>
      <ul>
        <li>需要在飞书开放平台创建应用并获取相关凭证</li>
        <li>配置事件订阅URL以接收消息事件</li>
        <li>确保应用已获得必要的权限</li>
        <li>支持企业内部和外部用户交互</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, onMounted } from 'vue'

// 定义属性
const props = defineProps<{
  modelValue: Record<string, any>
}>()

// 定义事件
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  'validate': [isValid: boolean]
}>()

// 初始化默认值
const initDefaults = () => {
  const defaults = {
    app_id: '',
    app_secret: '',
    verification_token: '',
    encrypt_key: '',
    bot_type: 'custom',
    permissions: ['im:message']
  }
  
  // 合并默认值
  const mergedValue = { ...defaults, ...props.modelValue }
  emit('update:modelValue', mergedValue)
}

// 处理值变化
const handleChange = () => {
  emit('update:modelValue', props.modelValue)
  validateConfig()
}

// 验证配置
const validateConfig = () => {
  const isValid = !!(
    props.modelValue.app_id && 
    props.modelValue.app_secret && 
    props.modelValue.verification_token
  )
  emit('validate', isValid)
}

// 监听值变化
watch(() => props.modelValue, validateConfig, { deep: true })

onMounted(() => {
  initDefaults()
})
</script>

<style scoped>
.feishu-config {
  padding: 16px 0;
}

.config-description {
  margin-top: 16px;
  padding: 12px;
  background: var(--el-bg-color-page);
  border-radius: 6px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.config-description p {
  margin: 0 0 8px 0;
  font-weight: 500;
}

.config-description ul {
  margin: 0;
  padding-left: 16px;
}

.config-description li {
  margin-bottom: 4px;
}
</style>