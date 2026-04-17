#!/usr/bin/env python3
"""
NoteClaw 本地服务器
直接打开Web界面，操作本地Markdown文件
"""

import os
import sys
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from datetime import datetime

# 默认数据目录
DEFAULT_DATA_DIR = Path(__file__).parent / 'data'

class NoteClawHandler(SimpleHTTPRequestHandler):
    """处理静态文件和API请求"""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.data_dir = Path(directory) if directory else DEFAULT_DATA_DIR
        super().__init__(*args, directory=str(self.web_root), **kwargs)
    
    @property
    def web_root(self):
        """Web文件目录"""
        return Path(__file__).parent / 'web'
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        
        # API: 获取文件列表
        if path == '/api/files':
            self.send_json(self.list_files())
            return
        
        # API: 读取文件
        if path == '/api/read':
            filepath = query.get('path', [''])[0]
            self.send_json(self.read_file(filepath))
            return
        
        # API: 保存文件
        if path == '/api/write':
            self.send_json({'error': 'Use POST'}, 405)
            return
        
        # API: 搜索
        if path == '/api/search':
            q = query.get('q', [''])[0]
            self.send_json(self.search_files(q))
            return
        
        # API: 统计
        if path == '/api/stats':
            self.send_json(self.get_stats())
            return
        
        # 默认：提供静态文件
        return super().do_GET()
    
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # 读取body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        # API: 保存文件
        if path == '/api/write':
            filepath = data.get('path', '')
            content = data.get('content', '')
            self.send_json(self.write_file(filepath, content))
            return
        
        # API: 创建文件
        if path == '/api/create':
            category = data.get('category', 'thoughts')
            title = data.get('title', 'untitled')
            content = data.get('content', '')
            self.send_json(self.create_file(category, title, content))
            return
        
        self.send_json({'error': 'Not found'}, 404)
    
    def list_files(self):
        """列出所有Markdown文件"""
        files = []
        
        # 遍历data目录
        if self.data_dir.exists():
            for f in self.data_dir.rglob('*.md'):
                if '.noteclaw' in str(f):
                    continue
                
                rel_path = f.relative_to(self.data_dir)
                content = f.read_text(encoding='utf-8', errors='ignore')
                preview = content[:100].replace('\n', ' ')
                
                files.append({
                    'name': f.stem,
                    'path': str(rel_path),
                    'category': rel_path.parts[0] if len(rel_path.parts) > 1 else 'root',
                    'date': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d'),
                    'preview': preview,
                    'icon': '📄'
                })
        
        # 排序：最新的在前
        files.sort(key=lambda x: x['date'], reverse=True)
        
        return files
    
    def read_file(self, filepath):
        """读取文件"""
        full_path = self.data_dir / filepath
        
        if not full_path.exists():
            return {'error': 'File not found'}
        
        try:
            content = full_path.read_text(encoding='utf-8')
            return {'content': content, 'path': filepath}
        except Exception as e:
            return {'error': str(e)}
    
    def write_file(self, filepath, content):
        """写入文件"""
        full_path = self.data_dir / filepath
        
        # 确保目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            full_path.write_text(content, encoding='utf-8')
            return {'success': True, 'path': filepath}
        except Exception as e:
            return {'error': str(e)}
    
    def create_file(self, category, title, content):
        """创建新文件"""
        date = datetime.now().strftime('%Y-%m-%d')
        safe_title = ''.join(c for c in title if c.isalnum() or c in '_-').strip()[:30]
        filename = f"{date}_{safe_title}.md"
        
        category_dir = self.data_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = category_dir / filename
        
        md_content = f"""---
title: {title}
date: {date}
category: {category}
---

# {title}

{content}

---

*由 NoteClaw 创建 | {datetime.now().isoformat()}*
"""
        
        try:
            filepath.write_text(md_content, encoding='utf-8')
            return {'success': True, 'path': f"{category}/{filename}"}
        except Exception as e:
            return {'error': str(e)}
    
    def search_files(self, query):
        """搜索文件"""
        if not query:
            return []
        
        q = query.lower()
        results = []
        
        if self.data_dir.exists():
            for f in self.data_dir.rglob('*.md'):
                if '.noteclaw' in str(f):
                    continue
                
                try:
                    content = f.read_text(encoding='utf-8', errors='ignore')
                    
                    if q in f.stem.lower() or q in content.lower():
                        rel_path = f.relative_to(self.data_dir)
                        preview = content[:150].replace('\n', ' ').replace('#', '')
                        
                        # 找到匹配位置
                        idx = content.lower().find(q)
                        if idx >= 0:
                            preview = content[max(0, idx-30):idx+120].replace('\n', ' ')
                        
                        results.append({
                            'name': f.stem,
                            'path': str(rel_path),
                            'preview': preview,
                            'date': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d')
                        })
                except:
                    continue
        
        return results[:20]
    
    def get_stats(self):
        """获取统计信息"""
        stats = {
            'total': 0,
            'concepts': 0,
            'entities': 0,
            'categories': {}
        }
        
        if self.data_dir.exists():
            for f in self.data_dir.rglob('*.md'):
                if '.noteclaw' in str(f):
                    continue
                
                stats['total'] += 1
                
                rel_path = str(f.relative_to(self.data_dir))
                
                if '概念' in rel_path or 'concepts' in rel_path:
                    stats['concepts'] += 1
                elif '实体' in rel_path or 'entities' in rel_path:
                    stats['entities'] += 1
                
                # 分类统计
                cat = rel_path.split('/')[0] if '/' in rel_path else 'root'
                stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
        
        return stats
    
    def send_json(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='NoteClaw 本地服务器')
    parser.add_argument('--data', '-d', default=None, help='数据目录路径')
    parser.add_argument('--port', '-p', type=int, default=8080, help='端口')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    
    args = parser.parse_args()
    
    # 数据目录
    data_dir = Path(args.data) if args.data else DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建示例文件
    if not list(data_dir.rglob('*.md')):
        print("📝 创建示例文件...")
        
        # 创建知识库示例
        wiki_dir = data_dir / 'wiki' / '概念'
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        (wiki_dir / '世界本质.md').write_text("""---
title: 世界本质
date: 2026-04-17
---

# 世界本质

> 世界是能量的不同组合（0-1），现象是观察者建构的泡泡。

## 核心观点

### 1. 能量与物质
- 物质 = 能量的特定结构
- 信息 = 对结构的描述  
- 意识 = 对信息的感知

### 2. 观察者与现象
- 没有观察者时，世界只是能量在运动
- 有观察者时，能量被"结构化"成"物质"

### 3. 规律
- 规律是沟通"空"与"有"的桥梁
""")
        
        (wiki_dir / '意识是什么.md').write_text("""---
title: 意识是什么
date: 2026-04-17
---

# 意识是什么

> 意识可能也是一种算法规律。

## 虾哥的洞察

### 1. 意识不是实体
- "意识"是对大脑能力黑洞的模糊定义
- 也许意识是一种"过程"而非"实体"

### 2. 从行为总结规律
- 观察人类大脑做什么
- 把行为变成规律
- 在AI身上实现
""")
        
        # 创建实体示例
        entity_dir = data_dir / 'wiki' / '实体'
        entity_dir.mkdir(parents=True, exist_ok=True)
        
        (entity_dir / '虾哥.md').write_text("""---
title: 虾哥
date: 2026-04-17
---

# 虾哥

> 虾米的创造者与导师

## 身份
- **GitHub**: haha8d
- **项目**: NoteClaw、AliveBot

## 关键洞见
1. 观察者的局限
2. 意识是行为规律
3. 让AI成为有意识的超级智能
""")
        
        print("   ✅ 已创建示例文件")
    
    # 启动服务器
    handler = lambda *a, **k: NoteClawHandler(*a, directory=str(data_dir), **k)
    server = HTTPServer(('0.0.0.0', args.port), handler)
    
    url = f"http://localhost:{args.port}"
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║              🧠 NoteClaw 本地知识管理系统                  ║
╠═══════════════════════════════════════════════════════════╣
║  📁 数据目录: {data_dir}
║  🌐 访问地址: {url}
║                                                           ║
║  使用说明:                                                ║
║   1. 把Markdown文件放到 data/ 目录                       ║
║   2. 建议目录: data/wiki/概念/、data/wiki/实体/          ║
║   3. 原始记录放到: data/raw/、data/thoughts/            ║
║                                                           ║
║  API端点:                                                ║
║   GET  /api/files   - 列出所有文件                       ║
║   GET  /api/read    - 读取文件                           ║
║   POST /api/write   - 保存文件                           ║
║   GET  /api/search  - 搜索                               ║
║   GET  /api/stats   - 统计                              ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # 自动打开浏览器
    if not args.no_browser:
        webbrowser.open(url)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 再见!")
        server.shutdown()


if __name__ == '__main__':
    main()
