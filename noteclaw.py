#!/usr/bin/env python3
"""
NoteClaw - AI友好知识管理系统
融合 Karpathy Wiki 风格知识库
"""

import os
import sys
import json
import argparse
from pathlib import Path

from core.core import NoteClawCore
from core.ai import NoteClawAI
from core.wiki import NoteClawWiki

NOTECLAW_DIR = Path(os.environ.get('NOTECLAW_DIR', Path.home() / '.noteclaw'))

class NoteClaw:
    """
    NoteClaw 主入口
    
    整合四大能力：
    1. 索引 - SQLite + ChromaDB
    2. AI - 抓取 + 提炼
    3. Wiki - Karpathy知识库
    4. API - REST服务
    """
    
    def __init__(self, root_dir: str = None):
        self.root = Path(root_dir) if root_dir else NOTECLAW_DIR
        self.core = NoteClawCore(str(self.root))
        self.ai = NoteClawAI(str(self.root))
        self.wiki = NoteClawWiki(str(self.root))
    
    # ========== 索引能力 ==========
    
    def index(self) -> int:
        """索引所有笔记"""
        return self.core.index_all()
    
    def search(self, query: str, mode: str = 'text', limit: int = 10):
        """搜索
        
        Args:
            query: 查询内容
            mode: 模式 (text/vector/tag)
            limit: 返回数量
        """
        if mode == 'text':
            return self.core.search_text(query, limit)
        elif mode == 'vector':
            return self.core.search_vector(query, limit)
        elif mode == 'tag':
            return self.core.search_tag(query)
        else:
            return self.core.search_text(query, limit)
    
    def stats(self) -> dict:
        """统计信息"""
        return self.core.get_stats()
    
    # ========== AI能力 ==========
    
    def fetch(self, url: str, save: bool = True, category: str = 'references') -> dict:
        """抓取网页"""
        return self.ai.fetch_url(url, save, category)
    
    def distill(self, text: str, mode: str = 'summary', save: bool = False, title: str = None) -> dict:
        """提炼文本"""
        return self.ai.distill(text, mode, save, title)
    
    # ========== Wiki能力 ==========
    
    def ingest(self, source: str, category: str = 'articles') -> str:
        """摄入原始资料"""
        return self.wiki.ingest(source, category)
    
    def compile(self, force: bool = False) -> dict:
        """编译Wiki"""
        return self.wiki.compile(force)
    
    def query_wiki(self, question: str) -> list:
        """查询Wiki"""
        return self.wiki.query(question)
    
    def lint(self) -> dict:
        """检查健康度"""
        return self.wiki.lint()
    
    def audit(self) -> dict:
        """处理反馈"""
        return self.wiki.audit()
    
    # ========== 原始记录能力 ==========
    
    def log_thought(self, content: str, category: str = 'thoughts') -> str:
        """记录思考（原始数据）"""
        from datetime import datetime
        import re
        
        date = datetime.now().strftime('%Y-%m-%d')
        time = datetime.now().strftime('%H:%M')
        
        # 生成文件名
        safe_content = re.sub(r'[^\w\s]', '', content[:30]).replace(' ', '_')
        filename = f"{date}_{time}_{safe_content}.md"
        
        log_dir = self.root / 'raw' / category
        log_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = log_dir / filename
        
        content_md = f"""---
title: {content[:50]}
date: {date}
time: {time}
type: thought
category: {category}
---

# {content[:100]}

{content}

---
*由 NoteClaw 自动记录 | {datetime.now().isoformat()}*
"""
        
        filepath.write_text(content_md, encoding='utf-8')
        
        # 自动索引
        self.core.index_note(str(filepath))
        
        return str(filepath)
    
    def auto_compile(self) -> dict:
        """自动编译：定时把raw笔记整理成wiki"""
        return self.wiki.compile()
    
    def close(self):
        """关闭连接"""
        self.core.close()


# ========== CLI 接口 ==========

def main():
    parser = argparse.ArgumentParser(
        description='NoteClaw - AI友好知识管理系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 索引
  noteclaw index
  
  # 搜索
  noteclaw search "什么是意识"
  noteclaw search "什么是意识" --mode vector
  
  # 抓取
  noteclaw fetch https://example.com/article
  
  # 提炼
  noteclaw distill file.md --mode summary
  
  # Wiki摄入
  noteclaw ingest https://example.com/article --category papers
  noteclaw ingest ./notes.md --category notes
  
  # Wiki编译
  noteclaw compile
  noteclaw compile --force
  
  # Wiki查询
  noteclaw query "意识的本质"
  
  # 健康检查
  noteclaw lint
  
  # 处理反馈
  noteclaw audit
  
  # 记录思考
  noteclaw log "今天我学到了..."
  
  # 自动整理
  noteclaw auto-compile
  
  # 统计
  noteclaw stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # index
    subparsers.add_parser('index', help='索引所有笔记')
    
    # search
    p_search = subparsers.add_parser('search', help='搜索笔记')
    p_search.add_argument('query', help='搜索内容')
    p_search.add_argument('--mode', choices=['text', 'vector', 'tag'], default='text', help='搜索模式')
    p_search.add_argument('--limit', type=int, default=10, help='返回数量')
    
    # fetch
    p_fetch = subparsers.add_parser('fetch', help='抓取网页')
    p_fetch.add_argument('url', help='网页URL')
    p_fetch.add_argument('--no-save', action='store_true', help='不保存')
    p_fetch.add_argument('--category', default='references', help='分类')
    
    # distill
    p_distill = subparsers.add_parser('distill', help='提炼文本')
    p_distill.add_argument('file', help='文本文件')
    p_distill.add_argument('--mode', default='summary', 
                          choices=['summary', 'keypoints', 'outline', 'qa', 'mindmap'],
                          help='提炼模式')
    p_distill.add_argument('--save', action='store_true', help='保存结果')
    p_distill.add_argument('--title', help='标题')
    
    # ingest
    p_ingest = subparsers.add_parser('ingest', help='Wiki摄入原始资料')
    p_ingest.add_argument('source', help='文件或URL')
    p_ingest.add_argument('--category', default='articles', help='分类')
    
    # compile
    p_compile = subparsers.add_parser('compile', help='Wiki编译')
    p_compile.add_argument('--force', action='store_true', help='强制重新编译')
    
    # query
    p_query = subparsers.add_parser('query', help='Wiki查询')
    p_query.add_argument('question', help='问题')
    
    # lint
    subparsers.add_parser('lint', help='Wiki健康检查')
    
    # audit
    subparsers.add_parser('audit', help='Wiki处理反馈')
    
    # log
    p_log = subparsers.add_parser('log', help='记录思考')
    p_log.add_argument('content', help='思考内容')
    p_log.add_argument('--category', default='thoughts', help='分类')
    
    # auto-compile
    subparsers.add_parser('auto-compile', help='自动整理')
    
    # stats
    subparsers.add_parser('stats', help='统计信息')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    nc = NoteClaw()
    
    try:
        if args.command == 'index':
            count = nc.index()
            print(f"已索引 {count} 个笔记")
        
        elif args.command == 'search':
            results = nc.search(args.query, args.mode, args.limit)
            for r in results:
                if 'path' in r:
                    print(f"{r.get('title', 'Untitled')}: {r['path']}")
                else:
                    print(f"{r.get('title', 'Untitled')} (distance: {r.get('distance', 0):.3f})")
        
        elif args.command == 'fetch':
            result = nc.fetch(args.url, not args.no_save, args.category)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        elif args.command == 'distill':
            text = Path(args.file).read_text(encoding='utf-8')
            result = nc.distill(text, args.mode, args.save, args.title)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        elif args.command == 'ingest':
            result = nc.ingest(args.source, args.category)
            print(f"Ingested: {result}")
        
        elif args.command == 'compile':
            result = nc.compile(args.force)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'query':
            results = nc.query_wiki(args.question)
            for r in results:
                print(f"\n## {r['title']}")
                for m in r['matches']:
                    print(f"  {m[:150]}...")
        
        elif args.command == 'lint':
            result = nc.lint()
            print(json.dumps(result, indent=2))
        
        elif args.command == 'audit':
            result = nc.audit()
            print(json.dumps(result, indent=2))
        
        elif args.command == 'log':
            result = nc.log_thought(args.content, args.category)
            print(f"Logged: {result}")
        
        elif args.command == 'auto-compile':
            result = nc.auto_compile()
            print(json.dumps(result, indent=2))
        
        elif args.command == 'stats':
            result = nc.stats()
            print(json.dumps(result, indent=2))
    
    finally:
        nc.close()


if __name__ == '__main__':
    main()
