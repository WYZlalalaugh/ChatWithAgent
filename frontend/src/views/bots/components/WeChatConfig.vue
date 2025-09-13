<template>
  <div class="wechat-config">
    <el-form-item label="微信号" prop="wechat_id">
      <el-input
        v-model="modelValue.wechat_id"
        placeholder="请输入微信号"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="登录方式">
      <el-radio-group v-model="modelValue.login_method" @change="handleChange">
        <el-radio label="qrcode">扫码登录</el-radio>
        <el-radio label="web">网页登录</el-radio>
      </el-radio-group>
    </el-form-item>
    
    <el-form-item label="自动通过好友申请">
      <el-switch
        v-model="modelValue.auto_accept_friend"
        @change="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="自动回复关键词">
      <el-input
        v-model="modelValue.auto_reply_keywords"
        type="textarea"
        :rows="3"
        placeholder="每行一个关键词，当收到包含这些关键词的消息时自动回复"
        @input="handleChange"
      />
    </el-form-item>
    
    <div class="config-description">
      <p>配置说明：</p>
      <ul>
        <li>微信登录需要扫码验证，请确保手机微信可用</li>
        <li>建议使用小号进行测试</li>
        <li>自动通过好友申请功能需谨慎使用</li>
        <li>支持群聊和私聊消息处理</li>
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
    wechat_id: '',
    login_method: 'qrcode',
    auto_accept_friend: false,
    auto_reply_keywords: ''
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
  const isValid = !!props.modelValue.wechat_id
  emit('validate', isValid)
}

// 监听值变化
watch(() => props.modelValue, validateConfig, { deep: true })

onMounted(() => {
  initDefaults()
})
</script>

<style scoped>
.wechat-config {
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