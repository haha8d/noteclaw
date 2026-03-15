# NoteClaw

> AI友好的个人知识管理系统

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

NoteClaw 是一个专为 AI 协作设计的本地笔记系统，采用纯 Markdown 格式，支持双向链接、全文搜索、向量语义搜索，并提供完整的 API 接口。

## ✨ 核心特性

- 🤖 **AI原生** - 纯 Markdown + YAML Frontmatter，AI 可直接读取处理
- 🔒 **隐私优先** - 本地存储，数据完全掌控
- 🔍 **智能搜索** - SQLite 全文搜索 + ChromaDB 向量语义搜索
- 🌐 **API接口** - 完整的 CRUD + AI 抓取/提炼接口
- 📝 **双向链接** - `[[笔记名]]` 语法实现知识关联
- 🚀 **简洁轻量** - 零依赖核心，渐进增强

## 🚀 快速开始

### 安装

```bash
# 方式1: pip 安装
pip install noteclaw

# 方式2: 源码安装
git clone https://github.com/haha8d/noteclaw.git
cd noteclaw
pip install -e .
```

### 初始化

```bash
noteclaw init ~/my-notes
cd ~/my-notes
```

### 启动服务器

```bash
noteclaw serve --port 8081
```

访问 http://localhost:8081/

## 📖 使用指南

### CLI 命令

```bash
# 基础操作
noteclaw create "标题" --content "内容"
noteclaw search "关键词"
noteclaw list

# AI 功能
noteclaw fetch "https://example.com/article"
noteclaw distill article.txt --mode summary

# API Token 管理
noteclaw token create --name "AI Assistant"
```

### API 接口

```bash
# 创建笔记
curl -X POST http://localhost:8081/api/note \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "新笔记", "content": "内容"}'

# 抓取网页
curl -X POST http://localhost:8081/api/fetch \
  -H "Authorization: Bearer <token>" \
  -d '{"url": "https://example.com"}'

# 提炼文本
curl -X POST http://localhost:8081/api/distill \
  -H "Authorization: Bearer <token>" \
  -d '{"text": "长文本...", "mode": "summary"}'
```

## 🏗️ 架构

```
noteclaw/
├── core/           # 核心引擎
│   ├── __init__.py
│   ├── database.py # SQLite 索引
│   └── vector.py   # ChromaDB 向量索引
├── cli/            # 命令行工具
│   ├── __init__.py
│   └── main.py
├── api/            # HTTP API
│   ├── __init__.py
│   └── server.py
└── web/            # Web 界面
    └── index.html
```

## 📚 文档

- [安装指南](docs/install.md)
- [API 文档](docs/api.md)
- [AI 接口文档](docs/ai-api.md)
- [架构设计](docs/architecture.md)

## 🤝 贡献

欢迎贡献代码！请阅读 [贡献指南](CONTRIBUTING.md)。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 链接

- [GitHub](https://github.com/haha8d/noteclaw)
- [文档站点](https://haha8d.github.io/noteclaw)

---

Made with ❤️ by [haha8d](https://github.com/haha8d)
