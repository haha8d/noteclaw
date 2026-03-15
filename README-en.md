# NoteClaw

[中文](README.md) | **English**

> AI-Friendly Personal Knowledge Management System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

NoteClaw is a local-first note-taking system designed for AI collaboration. It uses pure Markdown format, supports bidirectional linking, full-text search, vector semantic search, and provides a complete API interface.

## ✨ Core Features

- 🤖 **AI-Native** - Pure Markdown + YAML Frontmatter, AI can read and process directly
- 🔒 **Privacy First** - Local storage, full data ownership
- 🔍 **Smart Search** - SQLite full-text search + ChromaDB vector semantic search
- 🌐 **API Interface** - Complete CRUD + AI fetch/distill APIs
- 📝 **Bidirectional Links** - `[[Note Name]]` syntax for knowledge association
- 🚀 **Lightweight** - Zero-dependency core, progressive enhancement

## 🚀 Quick Start

### Installation

```bash
# Method 1: pip install
pip install noteclaw

# Method 2: Install from source
git clone https://github.com/haha8d/noteclaw.git
cd noteclaw
pip install -e .
```

### Initialize

```bash
noteclaw init ~/my-notes
cd ~/my-notes
```

### Start Server

```bash
noteclaw serve --port 8081
```

Visit http://localhost:8081/

## 📖 Usage Guide

### CLI Commands

```bash
# Basic operations
noteclaw create "Title" --content "Content"
noteclaw search "keyword"
noteclaw list

# AI features
noteclaw fetch "https://example.com/article"
noteclaw distill article.txt --mode summary

# API Token management
noteclaw token create --name "AI Assistant"
```

### API Interface

```bash
# Create note
curl -X POST http://localhost:8081/api/note \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "New Note", "content": "Content"}'

# Fetch webpage
curl -X POST http://localhost:8081/api/fetch \
  -H "Authorization: Bearer <token>" \
  -d '{"url": "https://example.com"}'

# Distill text
curl -X POST http://localhost:8081/api/distill \
  -H "Authorization: Bearer <token>" \
  -d '{"text": "Long text...", "mode": "summary"}'
```

## 🏗️ Architecture

```
noteclaw/
├── core/           # Core engine
│   ├── __init__.py
│   ├── database.py # SQLite index
│   └── vector.py   # ChromaDB vector index
├── cli/            # CLI tool
│   ├── __init__.py
│   └── main.py
├── api/            # HTTP API
│   ├── __init__.py
│   └── server.py
└── web/            # Web interface
    └── index.html
```

## 📚 Documentation

- [Installation Guide](docs/install-en.md)
- [API Documentation](docs/api-en.md)
- [AI API Documentation](docs/ai-api-en.md)
- [Architecture Design](docs/architecture-en.md)

## 🤝 Contributing

Contributions are welcome! Please read [Contributing Guide](CONTRIBUTING.md).

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🔗 Links

- [GitHub](https://github.com/haha8d/noteclaw)
- [Documentation Site](https://haha8d.github.io/noteclaw)

---

Made with ❤️ by [haha8d](https://github.com/haha8d)
