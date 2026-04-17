# NoteClaw 🧠

> 本地优先的AI知识管理系统 - 你的数据100%保存在本地

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ⚠️ 重要：数据隐私

```
┌─────────────────────────────────────────────────────────────┐
│  🔒 你的数据100%保存在本地                                  │
│                                                             │
│  • 不上传云端                                               │
│  • 不需要联网也能使用                                        │
│  • 敏感知识建议只在本机运行                                  │
│  • 如需局域网访问，请设置密码                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ 特性

- 🤖 **AI原生** - 专为AI协作设计
- 🔒 **本地优先** - 数据完全保存在本地
- 📝 **Markdown** - 纯文本，可备份、可版本控制
- 🔗 **双向链接** - `[[笔记名]]` 知识关联
- 💬 **AI对话** - 基于知识库的智能问答
- 🎨 **Web界面** - 浏览器直接渲染Markdown

---

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/haha8d/noteclaw.git
cd noteclaw

# 2. 启动（推荐本机模式）
python launcher.py

# 3. 打开浏览器
# 访问 http://localhost:8080
```

---

## 📖 详细用法

### 命令行选项

```bash
python launcher.py [选项]

选项:
  --data, -d        数据目录（默认: ./data）
  --port, -p        端口（默认: 8080）
  --password, -pwd  访问密码（可选）
  --host            绑定地址
                    localhost = 仅本机访问
                    0.0.0.0   = 局域网可访问
  --no-browser      不自动打开浏览器
```

### 推荐用法

```bash
# 本机私密使用（推荐）
python launcher.py

# 局域网共享（需设置密码）
python launcher.py --host 0.0.0.0 --password your_password

# 指定数据目录
python launcher.py --data ~/my-notes
```

---

## 📁 目录结构

```
noteclaw/
├── launcher.py       # 启动器
├── web/
│   └── index.html   # Web界面
├── data/            # 数据目录（你的笔记）
│   ├── wiki/
│   │   ├── 概念/   # 概念页
│   │   └── 实体/   # 实体页
│   └── raw/        # 原始记录
└── README.md
```

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Web 界面 (浏览器)                    │
│    📝 记录 | 📚 知识库 | 🔍 搜索 | 💬 AI对话           │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              本地 Python 服务器                          │
│    • 文件读写 API                                        │
│    • Markdown 渲染                                       │
│    • 搜索引擎                                            │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              本地文件系统 (你的数据)                      │
│    • data/wiki/概念/*.md                                │
│    • data/wiki/实体/*.md                                 │
│    • data/raw/*.md                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 安全建议

1. **敏感内容只在本机运行** - 不暴露到局域网
2. **定期备份** - `data/` 目录复制一份
3. **版本控制** - 用 Git 管理 `data/` 目录
4. **局域网访问必须设密码** - `--password`

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

Made with ❤️ by [haha8d](https://github.com/haha8d)
