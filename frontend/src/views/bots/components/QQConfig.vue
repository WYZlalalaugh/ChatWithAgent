<template>
  <div class="qq-config">
    <el-form-item label="QQ号" prop="qq_number">
      <el-input
        v-model="modelValue.qq_number"
        placeholder="请输入机器人QQ号"
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="密码" prop="password">
      <el-input
        v-model="modelValue.password"
        type="password"
        placeholder="请输入QQ密码"
        show-password
        @input="handleChange"
      />
    </el-form-item>
    
    <el-form-item label="登录方式">
      <el-radio-group v-model="modelValue.login_method" @change="handleChange">
        <el-radio label="password">密码登录</el-radio>
        <el-radio label="qrcode">扫码登录</el-radio>
      </el-radio-group>
    </el-form-item>
    
    <el-form-item label="协议类型">
      <el-select v-model="modelValue.protocol" placeholder="请选择协议类型" @change="handleChange">
        <el-option label="Android手机" value="android_phone" />
        <el-option label="Android平板" value="android_pad" />
        <el-option label="iPad" value="ipad" />
        <el-option label="MacOS" value="macos" />
      </el-select>
    </el-form-item>
    
    <div class="config-description">
      <p>配置说明：</p>
      <ul>
        <li>建议使用小号进行测试，避免封号风险</li>
        <li>首次登录可能需要验证码或设备验证</li>
        <li>协议类型影响功能可用性，推荐使用Android手机协议</li>
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
    qq_number: '',
    password: '',
    login_method: 'password',
    protocol: 'android_phone'
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
  const isValid = !!(props.modelValue.qq_number && props.modelValue.password)
  emit('validate', isValid)
}

// 监听值变化
watch(() => props.modelValue, validateConfig, { deep: true })

onMounted(() => {
  initDefaults()
})
</script>

<style scoped>
.qq-config {
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