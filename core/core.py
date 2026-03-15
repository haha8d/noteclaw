#!/usr/bin/env python3
"""
NoteClaw Core - 轻量级混合索引
SQLite + ChromaDB 双索引，保持简洁
"""

import sqlite3
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import hashlib

# 可选：向量搜索
try:
    import chromadb
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False

class NoteClawCore:
    """NoteClaw 核心索引引擎"""
    
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.db_path = self.root / ".noteclaw" / "index.db"
        self.chroma_path = self.root / ".noteclaw" / "chroma"
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化 SQLite
        self._init_sqlite()
        
        # 初始化 ChromaDB（可选）
        self.chroma_client = None
        self.collection = None
        self.embedder = None
        if VECTOR_SEARCH_AVAILABLE:
            self._init_chroma()
    
    def _init_sqlite(self):
        """初始化 SQLite 数据库"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        # 笔记表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                created TEXT,
                updated TEXT,
                tags TEXT,
                category TEXT,
                status TEXT,
                word_count INTEGER,
                checksum TEXT
            )
        """)
        
        # 链接表（双向链接）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                from_note TEXT,
                to_note TEXT,
                PRIMARY KEY (from_note, to_note)
            )
        """)
        
        # 全文搜索索引
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title, content, tags,
                content='notes',
                content_rowid='rowid'
            )
        """)
        
        self.conn.commit()
    
    def _init_chroma(self):
        """初始化 ChromaDB（可选）"""
        try:
            self.chroma_client = chromadb.PersistentClient(path=str(self.chroma_path))
            self.collection = self.chroma_client.get_or_create_collection("notes")
            
            if EMBEDDING_AVAILABLE:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"ChromaDB 初始化失败: {e}")
    
    def _parse_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """解析 YAML Frontmatter"""
        meta = {}
        body = content
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = parts[1].strip()
                body = parts[2].strip()
                
                # 简单解析 key: value
                for line in fm.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        meta[key.strip()] = value.strip().strip('"').strip("'")
        
        return meta, body
    
    def _extract_links(self, content: str) -> List[str]:
        """提取双向链接 [[笔记名]]"""
        pattern = r'\[\[([^\]]+)\]\]'
        return re.findall(pattern, content)
    
    def index_note(self, file_path: str) -> bool:
        """索引单个笔记"""
        path = Path(file_path)
        if not path.exists():
            return False
        
        try:
            content = path.read_text(encoding='utf-8')
            meta, body = self._parse_frontmatter(content)
            
            note_id = hashlib.md5(str(path).encode()).hexdigest()[:16]
            rel_path = str(path.relative_to(self.root))
            
            # 计算校验和
            checksum = hashlib.md5(content.encode()).hexdigest()
            
            # 检查是否需要更新
            cursor = self.conn.execute(
                "SELECT checksum FROM notes WHERE path = ?", (rel_path,)
            )
            row = cursor.fetchone()
            if row and row['checksum'] == checksum:
                return False  # 未变化
            
            # 插入/更新 SQLite
            self.conn.execute("""
                INSERT OR REPLACE INTO notes 
                (id, path, title, content, created, updated, tags, category, status, word_count, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note_id,
                rel_path,
                meta.get('title', path.stem),
                body,
                meta.get('created', ''),
                meta.get('updated', meta.get('created', '')),
                meta.get('tags', ''),
                meta.get('category', ''),
                meta.get('status', ''),
                len(body.split()),
                checksum
            ))
            
            # 更新全文索引
            self.conn.execute("""
                INSERT OR REPLACE INTO notes_fts (rowid, title, content, tags)
                SELECT rowid, title, content, tags FROM notes WHERE id = ?
            """, (note_id,))
            
            # 更新链接
            self.conn.execute("DELETE FROM links WHERE from_note = ?", (note_id,))
            for link in self._extract_links(content):
                link_id = hashlib.md5(link.encode()).hexdigest()[:16]
                self.conn.execute(
                    "INSERT OR IGNORE INTO links (from_note, to_note) VALUES (?, ?)",
                    (note_id, link_id)
                )
            
            self.conn.commit()
            
            # 更新向量索引（可选）
            if self.collection and self.embedder:
                embedding = self.embedder.encode(f"{meta.get('title', '')} {body[:1000]}")
                self.collection.upsert(
                    ids=[note_id],
                    embeddings=[embedding.tolist()],
                    metadatas=[{
                        'path': rel_path,
                        'title': meta.get('title', path.stem),
                        'tags': meta.get('tags', '')
                    }],
                    documents=[body[:2000]]
                )
            
            return True
            
        except Exception as e:
            print(f"索引失败 {file_path}: {e}")
            return False
    
    def index_all(self) -> int:
        """索引所有笔记"""
        count = 0
        for md_file in self.root.rglob("*.md"):
            if ".noteclaw" not in str(md_file):
                if self.index_note(str(md_file)):
                    count += 1
        return count
    
    def search_text(self, query: str, limit: int = 10) -> List[Dict]:
        """全文搜索"""
        cursor = self.conn.execute("""
            SELECT n.* FROM notes n
            JOIN notes_fts fts ON n.rowid = fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_vector(self, query: str, limit: int = 5) -> List[Dict]:
        """向量语义搜索（需要 ChromaDB）"""
        if not self.collection or not self.embedder:
            return []
        
        embedding = self.embedder.encode(query)
        results = self.collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=limit
        )
        
        return [
            {
                'id': results['ids'][0][i],
                'path': results['metadatas'][0][i]['path'],
                'title': results['metadatas'][0][i]['title'],
                'distance': results['distances'][0][i]
            }
            for i in range(len(results['ids'][0]))
        ]
    
    def search_tag(self, tag: str) -> List[Dict]:
        """标签搜索"""
        cursor = self.conn.execute(
            "SELECT * FROM notes WHERE tags LIKE ?",
            (f"%{tag}%",)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """统计信息"""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM notes")
        total = cursor.fetchone()['count']
        
        cursor = self.conn.execute("SELECT SUM(word_count) as words FROM notes")
        words = cursor.fetchone()['words'] or 0
        
        return {
            'total_notes': total,
            'total_words': words,
            'vector_indexed': self.collection.count() if self.collection else 0
        }
    
    def close(self):
        """关闭连接"""
        self.conn.close()


# CLI 接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python core.py <command> [args]")
        print("Commands: index, search, vector, stats")
        sys.exit(1)
    
    cmd = sys.argv[1]
    root = "."
    
    if cmd == "index":
        nc = NoteClawCore(root)
        count = nc.index_all()
        print(f"Indexed {count} notes")
        nc.close()
    
    elif cmd == "search" and len(sys.argv) > 2:
        nc = NoteClawCore(root)
        results = nc.search_text(sys.argv[2])
        for r in results:
            print(f"{r['path']}: {r['title']}")
        nc.close()
    
    elif cmd == "vector" and len(sys.argv) > 2:
        nc = NoteClawCore(root)
        results = nc.search_vector(sys.argv[2])
        for r in results:
            print(f"{r['path']}: {r['title']} (distance: {r['distance']:.3f})")
        nc.close()
    
    elif cmd == "stats":
        nc = NoteClawCore(root)
        stats = nc.get_stats()
        print(json.dumps(stats, indent=2))
        nc.close()
