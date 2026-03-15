---
layout: default
title: NoteClaw
---

# NoteClaw

**[中文](#中文) | [English](#english)**

---

## 中文

> AI友好的个人知识管理系统

NoteClaw 是一个专为 AI 协作设计的本地笔记系统，采用纯 Markdown 格式，支持双向链接、全文搜索、向量语义搜索，并提供完整的 API 接口。

### ✨ 核心特性

- 🤖 **AI原生** - 纯 Markdown + YAML Frontmatter
- 🔒 **隐私优先** - 本地存储，数据完全掌控
- 🔍 **智能搜索** - SQLite 全文搜索 + ChromaDB 向量搜索
- 🌐 **API接口** - 完整的 CRUD + AI 抓取/提炼接口
- 📝 **双向链接** - `[[笔记名]]` 语法
- 🚀 **简洁轻量** - 零依赖核心

### 🚀 快速开始

```bash
pip install noteclaw
noteclaw init ~/my-notes
cd ~/my-notes
noteclaw serve --port 8081
```

访问 http://localhost:8081/

### 📖 文档

- [安装指南](docs/install.md)
- [API 文档](docs/api.md)
- [AI 接口文档](docs/ai-api.md)

### 🔗 链接

- [GitHub 仓库](https://github.com/haha8d/noteclaw)
- [PyPI 包](https://pypi.org/project/noteclaw/)

---

## English

> AI-Friendly Personal Knowledge Management System

NoteClaw is a local-first note-taking system designed for AI collaboration. It uses pure Markdown format, supports bidirectional linking, full-text search, vector semantic search, and provides a complete API interface.

### ✨ Core Features

- 🤖 **AI-Native** - Pure Markdown + YAML Frontmatter
- 🔒 **Privacy First** - Local storage, full data ownership
- 🔍 **Smart Search** - SQLite full-text + ChromaDB vector search
- 🌐 **API Interface** - Complete CRUD + AI fetch/distill APIs
- 📝 **Bidirectional Links** - `[[Note Name]]` syntax
- 🚀 **Lightweight** - Zero-dependency core

### 🚀 Quick Start

```bash
pip install noteclaw
noteclaw init ~/my-notes
cd ~/my-notes
noteclaw serve --port 8081
```

Visit http://localhost:8081/

### 📖 Documentation

- [Installation Guide](docs/install-en.md)
- [API Documentation](docs/api-en.md)
- [AI API Documentation](docs/ai-api-en.md)

### 🔗 Links

- [GitHub Repository](https://github.com/haha8d/noteclaw)
- [PyPI Package](https://pypi.org/project/noteclaw/)

---

Made with ❤️ by [haha8d](https://github.com/haha8d)
