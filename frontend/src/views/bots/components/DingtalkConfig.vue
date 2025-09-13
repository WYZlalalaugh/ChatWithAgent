<template>
  <div class="dingtalk-config">
    <el-form-item label="App Key" prop="app_key">
      <el-input
        v-model="modelValue.app_key"
        placeholder="请输入钉钉应用的App Key"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="App Secret" prop="app_secret">
      <el-input
        v-model="modelValue.app_secret"
        type="password"
        placeholder="请输入钉钉应用的App Secret"
        show-password
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="机器人Token" prop="robot_token">
      <el-input
        v-model="modelValue.robot_token"
        placeholder="请输入机器人的Webhook Token"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="加密Secret">
      <el-input
        v-model="modelValue.encrypt_secret"
        placeholder="请输入加密Secret（可选）"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="机器人类型">
      <el-radio-group v-model="modelValue.robot_type" @change="handleChange">
        <el-radio label="enterprise">企业内部应用</el-radio>
        <el-radio label="webhook">自定义机器人</el-radio>
      </el-radio-group>
    </el-form-item>
    
    <el-form-item label="消息类型">
      <el-checkbox-group v-model="modelValue.message_types" @change="handleChange">
        <el-checkbox label="text">文本消息</el-checkbox>
        <el-checkbox label="markdown">Markdown消息</el-checkbox>
        <el-checkbox label="link">链接消息</el-checkbox>
        <el-checkbox label="actionCard">卡片消息</el-checkbox>
      </el-checkbox-group>
    </el-form-item>
    
    <el-form-item label="@所有人权限">
      <el-switch
        v-model="modelValue.at_all_permission"
        @change="handleChange"
      />
    </el-form-item>
    
    <div class="config-description">
      <p>配置说明：</p>
      <ul>
        <li>需要在钉钉开放平台创建应用或自定义机器人</li>
        <li>企业内部应用需要管理员授权</li>
        <li>自定义机器人可直接添加到群聊</li>
        <li>支持丰富的消息格式和交互功能</li>
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
    app_key: '',
    app_secret: '',
    robot_token: '',
    encrypt_secret: '',
    robot_type: 'webhook',
    message_types: ['text'],
    at_all_permission: false
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
  let isValid = false
  
  if (props.modelValue.robot_type === 'enterprise') {
    isValid = !!(props.modelValue.app_key && props.modelValue.app_secret)
  } else {
    isValid = !!props.modelValue.robot_token
  }
  
  emit('validate', isValid)
}

// 监听值变化
watch(() => props.modelValue, validateConfig, { deep: true })

onMounted(() => {
  initDefaults()
})
</script>

<style scoped>
.dingtalk-config {
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