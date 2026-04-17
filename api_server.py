#!/usr/bin/env python3
"""
NoteClaw API 服务器
"""

import os
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import secrets
from datetime import datetime

from core import NoteClawCore
from core.ai import NoteClawAI
from core.wiki import NoteClawWiki

NOTECLAW_DIR = Path(os.environ.get('NOTECLAW_DIR', Path.home() / '.noteclaw'))

# 初始化
nc_core = NoteClawCore(str(NOTECLAW_DIR))
nc_ai = NoteClawAI(str(NOTECLAW_DIR))
nc_wiki = NoteClawWiki(str(NOTECLAW_DIR))

# Token管理
TOKENS_FILE = NOTECLAW_DIR / '.noteclaw' / 'tokens.json'

def load_tokens():
    if TOKENS_FILE.exists():
        return json.loads(TOKENS_FILE.read_text())
    return {}

def save_tokens(tokens):
    TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True')
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))

def verify_token(token: str, required_perm: str = 'read') -> bool:
    if not token:
        return False
    tokens = load_tokens()
    if token in tokens:
        perms = tokens[token].get('permissions', ['read'])
        if required_perm in perms or 'admin' in perms:
            tokens[token]['last_used'] = str(datetime.now())
            save_tokens(tokens)
            return True
    return False

def generate_token(name: str) -> str:
    token = secrets.token_urlsafe(32)
    tokens = load_tokens()
    tokens[token] = {
        'name': name,
        'created': str(datetime.now()),
        'permissions': ['read', 'write', 'search', 'ai', 'wiki']
    }
    save_tokens(tokens)
    return token

class APIHandler(BaseHTTPRequestHandler):
    """NoteClaw API 处理"""
    
    def log_message(self, format, *args):
        pass  # 静默日志
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def get_token(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth[7:]
        return ''
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        
        # 健康检查
        if path == '/health':
            self.send_json({'status': 'ok', 'time': str(datetime.now())})
            return
        
        # Token验证
        token = self.get_token()
        
        # === 索引模块 ===
        if path == '/api/stats':
            stats = nc_core.get_stats()
            # 添加Wiki统计
            wiki_stats = {
                'raw': len(list((NOTECLAW_DIR / 'raw').rglob('*.md'))) if (NOTECLAW_DIR / 'raw').exists() else 0,
                'wiki': len(list((NOTECLAW_DIR / 'wiki').rglob('*.md'))) if (NOTECLAW_DIR / 'wiki').exists() else 0,
            }
            stats.update(wiki_stats)
            self.send_json(stats)
            return
        
        if path == '/api/search':
            q = query.get('q', [''])[0]
            mode = query.get('mode', ['text'])[0]
            limit = int(query.get('limit', [10])[0])
            
            if mode == 'vector':
                results = nc_core.search_vector(q, limit)
            elif mode == 'tag':
                results = nc_core.search_tag(q)
            else:
                results = nc_core.search_text(q, limit)
            
            self.send_json(results)
            return
        
        # === Wiki模块 ===
        if path == '/api/wiki/stats':
            wiki_stats = {
                'raw': len(list((NOTECLAW_DIR / 'raw').rglob('*.md'))) if (NOTECLAW_DIR / 'raw').exists() else 0,
                'concepts': len(list((NOTECLAW_DIR / 'wiki' / 'concepts').rglob('*.md'))) if (NOTECLAW_DIR / 'wiki' / 'concepts').exists() else 0,
                'entities': len(list((NOTECLAW_DIR / 'wiki' / 'entities').rglob('*.md'))) if (NOTECLAW_DIR / 'wiki' / 'entities').exists() else 0,
            }
            self.send_json(wiki_stats)
            return
        
        if path == '/api/wiki/pages':
            pages = []
            wiki_dir = NOTECLAW_DIR / 'wiki'
            if wiki_dir.exists():
                for f in wiki_dir.rglob('*.md'):
                    rel = f.relative_to(wiki_dir)
                    pages.append({
                        'title': f.stem,
                        'path': str(rel),
                        'type': rel.parts[0] if len(rel.parts) > 1 else 'root'
                    })
            self.send_json(pages)
            return
        
        if path == '/api/wiki/query':
            q = query.get('q', [''])[0]
            results = nc_wiki.query(q)
            self.send_json(results)
            return
        
        if path == '/api/wiki/lint':
            result = nc_wiki.lint()
            self.send_json(result)
            return
        
        # === Token管理 ===
        if path == '/api/token/create':
            name = query.get('name', ['API Token'])[0]
            token = generate_token(name)
            self.send_json({'token': token, 'name': name})
            return
        
        # 404
        self.send_json({'error': 'Not found'}, 404)
    
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
        
        # === 记录模块 ===
        if path == '/api/log':
            content = data.get('content', '')
            category = data.get('category', 'thoughts')
            
            result = {
                'content': content,
                'category': category,
                'saved': True,
                'path': f'raw/{category}/log.md'
            }
            self.send_json(result)
            return
        
        # === 抓取模块 ===
        if path == '/api/fetch':
            url = data.get('url', '')
            category = data.get('category', 'references')
            save = data.get('save', True)
            
            result = nc_ai.fetch_url(url, save, category)
            self.send_json(result)
            return
        
        # === 提炼模块 ===
        if path == '/api/distill':
            text = data.get('text', '')
            mode = data.get('mode', 'summary')
            save = data.get('save', False)
            title = data.get('title', None)
            
            result = nc_ai.distill(text, mode, save, title)
            self.send_json(result)
            return
        
        # === Wiki模块 ===
        if path == '/api/wiki/ingest':
            source = data.get('source', '')
            category = data.get('category', 'articles')
            
            result = nc_wiki.ingest(source, category)
            self.send_json({'path': result})
            return
        
        if path == '/api/wiki/compile':
            force = data.get('force', False)
            result = nc_wiki.compile(force)
            self.send_json(result)
            return
        
        if path == '/api/wiki/audit':
            result = nc_wiki.audit()
            self.send_json(result)
            return
        
        # 404
        self.send_json({'error': 'Not found'}, 404)


def run_server(host='0.0.0.0', port=8081):
    """启动API服务器"""
    server = HTTPServer((host, port), APIHandler)
    print(f"🚀 NoteClaw API Server: http://{host}:{port}")
    print(f"📁 Data: {NOTECLAW_DIR}")
    print(f"\n可用端点:")
    print(f"  GET  /api/stats          - 统计信息")
    print(f"  GET  /api/search?q=xxx   - 搜索")
    print(f"  GET  /api/wiki/pages     - Wiki页面列表")
    print(f"  GET  /api/wiki/query?q=xxx - Wiki查询")
    print(f"  POST /api/log            - 记录思考")
    print(f"  POST /api/fetch          - 抓取URL")
    print(f"  POST /api/distill        - 提炼文本")
    print(f"  POST /api/wiki/compile   - 编译Wiki")
    print(f"\n示例:")
    print(f"  curl -X POST http://localhost:{port}/api/log -H 'Content-Type: application/json' -d '{{\"content\":\"test\"}}'")
    
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='NoteClaw API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host')
    parser.add_argument('--port', type=int, default=8081, help='Port')
    
    args = parser.parse_args()
    
    run_server(args.host, args.port)
