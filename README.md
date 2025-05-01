# Humanize AI 文本优化工具

## 项目概述
Humanize AI 是一个专业的 AI 文本优化工具，能够将 AI 生成的文本转换成更自然、更人性化的内容。该工具支持多语言处理（西班牙语、英语、中文），并提供多种文本优化模式。

## 技术架构

### 前端架构
- 纯静态网页实现（HTML + CSS + JavaScript）
- 响应式设计，支持移动端和桌面端
- 多语言支持
- 模块化的 UI 组件

### 后端架构
- Flask 框架
- RESTful API 设计
- DeepSeek API 集成
- 安全性和限流机制

## 核心功能模块

### 1. 文本处理模式
- 免费模式（Free）
- 标准模式（Standard）
- 学术模式（Academic）
- 简化模式（Simple）
- 正式模式（Formal）
- 非正式模式（Informal）
- 扩展模式（Expand）
- 缩短模式（Shorten）

### 2. 安全机制
- IP 请求限制
- 文本长度验证
- 敏感内容过滤
- CORS 安全配置

### 3. API 集成
- DeepSeek API 集成
- 错误处理机制
- 请求日志记录

### 4. 语言检测与处理
- 自动语言检测
- 多语言提示词系统
- 语言特定优化

## 项目文件结构
```
├── api/                    # API 相关文件
├── api_service.py         # 后端主服务
├── index.html            # 前端主页面
├── script.js             # 前端交互逻辑
├── styles.css            # 样式文件
├── requirements.txt      # Python 依赖
├── .env                 # 环境变量配置
└── vercel.json          # Vercel 部署配置
```

## 核心 API 端点
- `/api/humanize` - 文本优化处理接口
  - 方法：POST
  - 限流：每分钟 10 次请求
  - 每日最大请求数：100次/IP

## 安装和部署
1. 克隆项目仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量：
   - DEEPSEEK_API_KEY
   - DEEPSEEK_API_BASE
4. 运行服务：`python api_service.py`

## 使用限制
- 最大文本长度：5000 字符
- IP 请求限制：每天 100 次
- 每分钟请求限制：10 次

## 安全注意事项
- API 密钥保护
- 敏感内容过滤
- 请求限流
- CORS 安全配置

## 后续优化方向
1. 增加更多文本处理模式
2. 优化语言检测算法
3. 添加用户认证系统
4. 实现高级文本分析功能
5. 优化响应速度和性能
 
