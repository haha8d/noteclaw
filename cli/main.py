#!/usr/bin/env python3
"""
NoteClaw CLI - 完整版（含AI接口）
"""

import os
import sys
import json
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import secrets
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from core import NoteClawCore
from ai import NoteClawAI

NOTECLAW_DIR = Path(os.environ.get('NOTECLAW_DIR', Path.home() / '.noteclaw'))
TOKENS_FILE = NOTECLAW_DIR / '.noteclaw' / 'tokens.json'

def load_tokens():
    if TOKENS_FILE.exists():
        return json.loads(TOKENS_FILE.read_text())
    return {}

def save_tokens(tokens):
    TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))

def generate_token(name: str) -> str:
    token = secrets.token_urlsafe(32)
    tokens = load_tokens()
    tokens[token] = {
        'name': name,
        'created': str(datetime.now()),
        'permissions': ['read', 'write', 'search', 'ai']
    }
    save_tokens(tokens)
    return token

def verify_token(token: str, required_perm: str = 'read') -> bool:
    tokens = load_tokens()
    if token in tokens:
        perms = tokens[token].get('permissions', ['read'])
        if required_perm in perms or 'admin' in perms:
            tokens[token]['last_used'] = str(datetime.now())
            save_tokens(tokens)
            return True
    return False

# CLI 命令
def cmd_fetch(args):
    """抓取网页"""
    ai = NoteClawAI(NOTECLAW_DIR)
    result = ai.fetch_url(args.url, save=not args.no_save, category=args.category)
    ai.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_distill(args):
    """提炼文本"""
    text = Path(args.file).read_text(encoding='utf-8')
    ai = NoteClawAI(NOTECLAW_DIR)
    result = ai.distill(text, mode=args.mode, save=args.save, title=args.title)
    ai.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_serve(args):
    """启动 API 服务器"""
    port = args.port or 8081
    host = args.host or '127.0.0.1'
    
    class APIHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args): pass
        
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
            self.end_headers()
        
        def do_GET(self): self.handle_request('GET')
        def do_POST(self): self.handle_request('POST')
        def do_PUT(self): self.handle_request('PUT')
        def do_DELETE(self): self.handle_request('DELETE')
        
        def handle_request(self, method):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            
            body = {}
            if method in ['POST', 'PUT']:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body_data = self.rfile.read(content_length)
                    try: body = json.loads(body_data)
                    except: body = {'raw': body_data.decode()}
            
            auth = self.headers.get('Authorization', '')
            token = auth[7:] if auth.startswith('Bearer ') else query.get('token', [''])[0]
            
            routes = {
                ('GET', '/api/stats'): self.get_stats,
                ('GET', '/api/search'): self.search_notes,
                ('GET', '/api/notes'): self.list_notes,
                ('GET', '/api/note'): self.get_note,
                ('POST', '/api/note'): self.create_note,
                ('PUT', '/api/note'): self.update_note,
                ('DELETE', '/api/note'): self.delete_note,
                ('POST', '/api/fetch'): self.fetch_url,
                ('POST', '/api/distill'): self.distill_text,
            }
            
            handler = routes.get((method, path))
            if handler: handler(token, query, body)
            else: self.send_error(404)
        
        def check_auth(self, token, perm='read'):
            if not verify_token(token, perm):
                self.send_error(401, "Unauthorized")
                return False
            return True
        
        def send_json(self, data, status=200):
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
        
        def get_stats(self, token, query, body):
            if not self.check_auth(token): return
            nc = NoteClawCore(NOTECLAW_DIR)
            self.send_json(nc.get_stats())
            nc.close()
        
        def search_notes(self, token, query, body):
            if not self.check_auth(token): return
            nc = NoteClawCore(NOTECLAW_DIR)
            results = nc.search_text(query.get('q', [''])[0], int(query.get('limit', ['10'])[0]))
            self.send_json({'query': query.get('q'), 'results': results})
            nc.close()
        
        def list_notes(self, token, query, body):
            if not self.check_auth(token): return
            nc = NoteClawCore(NOTECLAW_DIR)
            cursor = nc.conn.execute("SELECT path, title, created, tags FROM notes LIMIT 100")
            self.send_json({'notes': [dict(r) for r in cursor.fetchall()]})
            nc.close()
        
        def get_note(self, token, query, body):
            if not self.check_auth(token): return
            path = query.get('path', [''])[0]
            content = (NOTECLAW_DIR / path).read_text(encoding='utf-8') if path else ''
            self.send_json({'path': path, 'content': content})
        
        def create_note(self, token, query, body):
            if not self.check_auth(token, 'write'): return
            path = body.get('path', f"topics/ideas/{datetime.now().strftime('%Y%m%d')}_{body.get('title', 'note').replace(' ', '_')}.md")
            filepath = NOTECLAW_DIR / path
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            date = datetime.now().strftime('%Y-%m-%d')
            content = f"""---
title: {body.get('title', 'Untitled')}
created: {date}
tags: {json.dumps(body.get('tags', []))}
---

{body.get('content', '')}
"""
            filepath.write_text(content, encoding='utf-8')
            nc = NoteClawCore(NOTECLAW_DIR)
            nc.index_note(str(filepath))
            nc.close()
            self.send_json({'success': True, 'path': path}, 201)
        
        def update_note(self, token, query, body):
            if not self.check_auth(token, 'write'): return
            path = body.get('path')
            filepath = NOTECLAW_DIR / path
            filepath.write_text(body.get('content', ''), encoding='utf-8')
            nc = NoteClawCore(NOTECLAW_DIR)
            nc.index_note(str(filepath))
            nc.close()
            self.send_json({'success': True})
        
        def delete_note(self, token, query, body):
            if not self.check_auth(token, 'write'): return
            path = query.get('path', [''])[0]
            filepath = NOTECLAW_DIR / path
            if filepath.exists():
                trash = NOTECLAW_DIR / '.noteclaw' / 'trash'
                trash.mkdir(parents=True, exist_ok=True)
                filepath.rename(trash / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filepath.name}")
            self.send_json({'success': True})
        
        def fetch_url(self, token, query, body):
            """抓取网页"""
            if not self.check_auth(token, 'ai'): return
            url = body.get('url') or query.get('url', [''])[0]
            category = body.get('category', 'references')
            
            ai = NoteClawAI(NOTECLAW_DIR)
            result = ai.fetch_url(url, save=True, category=category)
            ai.close()
            self.send_json(result)
        
        def distill_text(self, token, query, body):
            """提炼文本"""
            if not self.check_auth(token, 'ai'): return
            text = body.get('text', '')
            mode = body.get('mode', 'summary')
            save = body.get('save', False)
            title = body.get('title')
            
            ai = NoteClawAI(NOTECLAW_DIR)
            result = ai.distill(text, mode=mode, save=save, title=title)
            ai.close()
            self.send_json(result)
    
    server = HTTPServer((host, port), APIHandler)
    print(f"🚀 NoteClaw API Server: http://{host}:{port}/")
    print("\nAPI 端点:")
    print("   GET    /api/stats")
    print("   GET    /api/search?q=<query>")
    print("   GET    /api/notes")
    print("   GET    /api/note?path=<path>")
    print("   POST   /api/note  {path, title, content, tags}")
    print("   PUT    /api/note  {path, content}")
    print("   DELETE /api/note?path=<path>")
    print("   POST   /api/fetch  {url, category}  - 抓取网页")
    print("   POST   /api/distill  {text, mode, save}  - 提炼文本")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

def main():
    parser = argparse.ArgumentParser(description='NoteClaw - AI知识管理系统')
    subparsers = parser.add_subparsers(dest='command')
    
    # fetch
    p_fetch = subparsers.add_parser('fetch', help='抓取网页')
    p_fetch.add_argument('url', help='网页URL')
    p_fetch.add_argument('--no-save', action='store_true')
    p_fetch.add_argument('--category', default='references')
    
    # distill
    p_distill = subparsers.add_parser('distill', help='提炼文本')
    p_distill.add_argument('file', help='文本文件')
    p_distill.add_argument('--mode', default='summary', 
                          choices=['summary', 'keypoints', 'outline', 'qa', 'mindmap'])
    p_distill.add_argument('--save', action='store_true')
    p_distill.add_argument('--title')
    
    # serve
    p_serve = subparsers.add_parser('serve', help='启动API服务器')
    p_serve.add_argument('--port', type=int)
    p_serve.add_argument('--host')
    
    args = parser.parse_args()
    
    commands = {
        'fetch': cmd_fetch,
        'distill': cmd_distill,
        'serve': cmd_serve,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
