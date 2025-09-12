# 贡献指南

欢迎参与 ChatBot 平台的开发！本指南将帮助您了解如何为项目做出贡献。

## 开发环境设置

### 1. Fork 和克隆项目

```bash
# Fork 项目到您的 GitHub 账号
# 然后克隆到本地
git clone https://github.com/your-username/ChatAgent.git
cd ChatAgent
```

### 2. 设置开发环境

**后端环境:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**前端环境:**
```bash
cd frontend
npm install
```

### 3. 配置开发数据库

```bash
# 启动开发数据库
docker-compose up -d mysql redis qdrant

# 运行数据库迁移
cd backend
alembic upgrade head
```

## 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

**后端开发:**
```bash
cd backend
# 启动开发服务器
python -m app.main

# 运行测试
pytest
```

**前端开发:**
```bash
cd frontend
# 启动开发服务器
npm run dev

# 运行测试
npm run test
```

### 3. 代码质量检查

**Python 代码检查:**
```bash
cd backend
# 代码格式化
black .
isort .

# 代码检查
flake8
mypy .
```

**前端代码检查:**
```bash
cd frontend
# 代码检查和格式化
npm run lint
npm run type-check
```

### 4. 提交更改

```bash
git add .
git commit -m "feat: add new feature description"
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

1. 在 GitHub 上创建 Pull Request
2. 填写 PR 描述，说明更改内容
3. 等待代码审查和测试通过
4. 合并到主分支

## 代码规范

### Python 代码规范

- 使用 [Black](https://black.readthedocs.io/) 进行代码格式化
- 使用 [isort](https://pycqa.github.io/isort/) 整理导入
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 编码规范
- 使用类型注解提高代码可读性
- 编写单元测试覆盖新功能

**示例:**
```python
from typing import List, Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    """用户创建数据模型"""
    username: str
    email: str
    password: str
    

def create_user(user_data: UserCreate) -> Optional[User]:
    """创建新用户
    
    Args:
        user_data: 用户创建数据
        
    Returns:
        创建的用户对象，失败时返回 None
    """
    # 实现逻辑
    pass
```

### TypeScript 代码规范

- 使用 [ESLint](https://eslint.org/) 和 [Prettier](https://prettier.io/) 进行代码检查和格式化
- 使用 TypeScript 严格模式
- 组件使用 Composition API
- 使用 Pascal Case 命名组件
- 使用 camelCase 命名变量和函数

**示例:**
```typescript
interface User {
  id: string
  username: string
  email: string
  createdAt: Date
}

const UserCard = defineComponent({
  name: 'UserCard',
  props: {
    user: {
      type: Object as PropType<User>,
      required: true
    }
  },
  setup(props) {
    const formatDate = (date: Date): string => {
      return date.toLocaleDateString('zh-CN')
    }
    
    return {
      formatDate
    }
  }
})
```

## 测试指南

### 后端测试

使用 pytest 进行测试：

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api/test_bots.py

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html
```

**测试示例:**
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_create_bot():
    """测试创建机器人"""
    bot_data = {
        "name": "测试机器人",
        "description": "这是一个测试机器人",
        "platform_type": "qq"
    }
    
    response = client.post("/api/v1/bots", json=bot_data)
    assert response.status_code == 201
    assert response.json()["name"] == bot_data["name"]
```

### 前端测试

使用 Vitest 进行单元测试：

```bash
# 运行测试
npm run test

# 运行测试并监听文件变化
npm run test:watch
```

## 文档贡献

### API 文档

API 文档使用 FastAPI 自动生成，但需要完善以下内容：

1. **接口描述**: 为每个接口添加详细描述
2. **参数说明**: 说明每个参数的作用和格式
3. **响应示例**: 提供完整的响应示例
4. **错误码**: 说明可能的错误码和处理方式

**示例:**
```python
@router.post("/bots", response_model=BotResponse, status_code=201)
async def create_bot(
    bot_data: BotCreate,
    current_user: User = Depends(get_current_user)
) -> BotResponse:
    """创建新的聊天机器人
    
    创建一个新的聊天机器人实例，支持多种IM平台。
    
    Args:
        bot_data: 机器人创建数据
        current_user: 当前用户（自动注入）
        
    Returns:
        创建的机器人信息
        
    Raises:
        ValidationError: 当输入数据格式错误时
        PermissionError: 当用户权限不足时
    """
    # 实现逻辑
    pass
```

### 用户文档

1. **教程文档**: 更新用户使用教程
2. **配置文档**: 完善配置选项说明
3. **部署文档**: 更新部署指南
4. **插件文档**: 编写插件开发文档

## Issue 和 Bug 报告

### 报告 Bug

使用 [Bug Report 模板](.github/ISSUE_TEMPLATE/bug_report.md) 报告问题：

1. **问题描述**: 清楚地描述问题
2. **复现步骤**: 提供详细的复现步骤
3. **预期行为**: 说明预期的正确行为
4. **环境信息**: 提供操作系统、版本等信息
5. **截图/日志**: 如果可能，提供相关截图或日志

### 功能请求

使用 [Feature Request 模板](.github/ISSUE_TEMPLATE/feature_request.md) 提出新功能：

1. **功能描述**: 详细描述建议的功能
2. **使用场景**: 说明功能的使用场景
3. **实现方案**: 如果有想法，提供实现方案
4. **优先级**: 说明功能的重要性

## 发布流程

### 版本号规范

使用 [语义化版本](https://semver.org/lang/zh-CN/) 规范：

- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

### 发布检查清单

- [ ] 所有测试通过
- [ ] 代码审查完成
- [ ] 文档更新完整
- [ ] 版本号更新
- [ ] 更新日志编写
- [ ] 安全性检查
- [ ] 性能测试通过

## 社区行为准则

### 我们的承诺

为了营造一个开放和包容的环境，我们作为贡献者和维护者承诺：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员友善

### 不可接受的行为

- 使用性化的语言或图像
- 煽动、侮辱/贬损的评论，人身或政治攻击
- 公开或私下的骚扰
- 未经明确许可发布他人的私人信息
- 在专业环境中可能被认为不适当的其他行为

## 联系方式

- **GitHub Issues**: [提交问题](https://github.com/your-org/chatbot-platform/issues)
- **GitHub Discussions**: [参与讨论](https://github.com/your-org/chatbot-platform/discussions)
- **邮箱**: contribute@chatbot-platform.com

感谢您对 ChatBot 平台的贡献！🎉