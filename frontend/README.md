# ChatBot 管理面板前端

基于 Vue 3 + TypeScript + Element Plus 构建的现代化管理面板。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **UI 库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **构建工具**: Vite
- **HTTP 客户端**: Axios
- **图表库**: ECharts
- **代码编辑器**: Monaco Editor

## 目录结构

```
frontend/
├── public/                 # 静态资源
├── src/                   # 源代码
│   ├── api/              # API 接口
│   ├── assets/           # 资源文件
│   ├── components/       # 通用组件
│   ├── layouts/          # 布局组件
│   ├── router/           # 路由配置
│   ├── stores/           # 状态管理
│   ├── styles/           # 全局样式
│   ├── types/            # TypeScript 类型定义
│   ├── utils/            # 工具函数
│   ├── views/            # 页面组件
│   ├── App.vue           # 根组件
│   └── main.ts           # 入口文件
├── package.json          # 依赖配置
├── tsconfig.json         # TypeScript 配置
├── vite.config.ts        # Vite 配置
└── README.md
```

## 功能特性

- 🎨 **现代化设计**: 基于 Element Plus 的清爽界面
- 📱 **响应式布局**: 适配不同屏幕尺寸
- 🔐 **权限管理**: 基于角色的访问控制
- 📊 **数据可视化**: 丰富的图表展示
- 🌐 **国际化**: 多语言支持
- 🎯 **类型安全**: 完整的 TypeScript 支持
- ⚡ **快速开发**: 热重载和快速构建

## 开发命令

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint

# 类型检查
npm run type-check
```

## 环境配置

开发环境变量配置在 `.env.development` 文件中：

```env
VITE_APP_TITLE=ChatBot 管理面板
VITE_API_BASE_URL=http://localhost:8000
VITE_UPLOAD_URL=http://localhost:8000/api/v1/upload
```