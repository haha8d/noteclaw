#!/usr/bin/env python3
"""
NoteClaw Wiki - Karpathy风格知识库
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import hashlib

class NoteClawWiki:
    """
    Karpathy风格知识库
    
    核心理念：
    1. Divide and conquer - 每页400-1200字
    2. Mermaid for diagrams - 图表
    3. Raw只读 - 源文件不修改
    4. Audit反馈 - 人类纠正AI
    """
    
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.raw_dir = self.root / 'raw'
        self.wiki_dir = self.root / 'wiki'
        self.audit_dir = self.root / 'audit'
        self.log_dir = self.root / 'log'
        self.resolved_dir = self.audit_dir / 'resolved'
        
        # 确保目录存在
        for d in [self.raw_dir, self.wiki_dir, self.audit_dir, self.log_dir, self.resolved_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    # ========== 五个核心操作 ==========
    
    def ingest(self, source_path: str, category: str = 'articles') -> str:
        """
        Ingest: 摄入原始资料到raw目录
        
        Args:
            source_path: 源文件路径或URL
            category: 分类 (articles/papers/notes/refs)
        
        Returns:
            保存的路径
        """
        date = datetime.now().strftime('%Y%m%d')
        
        # 如果是URL，需要先抓取
        if source_path.startswith('http'):
            return self._ingest_url(source_path, category)
        
        # 如果是本地文件，复制到raw
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")
        
        dest_dir = self.raw_dir / category
        dest_dir.mkdir(exist_ok=True)
        
        dest = dest_dir / f"{date}_{source.name}"
        
        # 复制文件
        import shutil
        shutil.copy2(source, dest)
        
        self._log(f"ingest | {source_path} -> {dest}")
        
        return str(dest)
    
    def _ingest_url(self, url: str, category: str) -> str:
        """从URL抓取内容"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 提取标题
            title = soup.find('title')
            title = title.get_text().strip() if title else 'Untitled'
            
            # 提取正文
            article = soup.find('article') or soup.find('main') or soup.find('body')
            content = article.get_text() if article else resp.text[:5000]
            
            # 保存
            date = datetime.now().strftime('%Y%m%d')
            safe_title = re.sub(r'[^\w\s-]', '', title)[:50].replace(' ', '_')
            filename = f"{date}_{safe_title}.md"
            
            dest_dir = self.raw_dir / category
            dest_dir.mkdir(exist_ok=True)
            
            content_md = f"""---
title: {title}
source: {url}
date: {datetime.now().isoformat()}
tags: [{category}]
---

# {title}

> 原文: {url}

## 内容

{content}

---

*由 NoteClaw Wiki 自动抓取*
"""
            
            dest = dest_dir / filename
            dest.write_text(content_md, encoding='utf-8')
            
            self._log(f"ingest | {url} -> {dest}")
            
            return str(dest)
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def compile(self, force: bool = False) -> Dict:
        """
        Compile: 从raw材料编译wiki页面
        
        - 把长页面拆分成多个概念页
        - 合并相近页面
        - 重建index.md
        
        Args:
            force: 是否强制重新编译
        
        Returns:
            编译结果统计
        """
        stats = {
            'compiled': 0,
            'split': 0,
            'merged': 0,
            'errors': []
        }
        
        # 读取现有wiki
        index_file = self.wiki_dir / 'index.md'
        existing_pages = self._read_index() if index_file.exists() else {}
        
        # 遍历raw文件
        for raw_file in self.raw_dir.rglob('*.md'):
            try:
                content = raw_file.read_text(encoding='utf-8')
                meta, body = self._parse_frontmatter(content)
                
                title = meta.get('title', raw_file.stem)
                word_count = len(body.split())
                
                # 如果超过1200字，拆分
                if word_count > 1200:
                    self._split_page(title, body, meta)
                    stats['split'] += 1
                
                # 创建/更新概念页
                concept_file = self.wiki_dir / 'concepts' / f"{title}.md"
                concept_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 内容：摘要 + 原始链接
                compiled_content = self._compile_content(title, body, meta, raw_file)
                concept_file.write_text(compiled_content, encoding='utf-8')
                
                stats['compiled'] += 1
                
            except Exception as e:
                stats['errors'].append(f"{raw_file}: {str(e)}")
        
        # 重建index
        self._rebuild_index()
        
        self._log(f"compile | compiled:{stats['compiled']} split:{stats['split']}")
        
        return stats
    
    def _split_page(self, title: str, body: str, meta: Dict) -> List[str]:
        """拆分长页面为多个子页面"""
        # 按章节拆分
        sections = re.split(r'^##\s+', body, flags=re.MULTILINE)
        
        if len(sections) <= 1:
            # 没有章节，随机拆分
            words = body.split()
            chunk_size = 400
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            sections = chunks
        
        subfolder = self.wiki_dir / 'concepts' / title.lower().replace(' ', '_')
        subfolder.mkdir(parents=True, exist_ok=True)
        
        # 创建index
        index_content = f"""---
title: {title}
type: concept
---

# {title}

> 本页面已拆分为多个子页面

## 子页面

"""
        
        subfiles = []
        for i, section in enumerate(sections[1:], 1):  # 跳过第一个空元素
            if not section.strip():
                continue
            
            # 提取小标题
            lines = section.split('\n')
            subtitle = lines[0].strip() if lines else f"Part {i}"
            content = '\n'.join(lines[1:]) if len(lines) > 1 else section
            
            subfile_name = f"{i}_{subtitle[:30].replace(' ', '_')}.md"
            subfile = subfolder / subfile_name
            
            subfile_content = f"""---
title: {title} - {subtitle}
parent: {title}
---

# {subtitle}

{content}

---

*本页面由 NoteClaw Wiki 自动拆分*
"""
            
            subfile.write_text(subfile_content, encoding='utf-8')
            subfiles.append(subfile_name)
            index_content += f"- [[{subtitle}]]\n"
        
        # 写index
        (subfolder / 'index.md').write_text(index_content, encoding='utf-8')
        
        return subfiles
    
    def _compile_content(self, title: str, body: str, meta: Dict, source: Path) -> str:
        """编译内容：摘要 + 来源链接"""
        # 生成摘要（取前200字）
        summary = ' '.join(body.split()[:100])
        
        return f"""---
title: {title}
type: concept
source: {source}
date: {meta.get('date', '')}
tags: {meta.get('tags', '')}
---

# {title}

> 本页面由原始资料编译

## 摘要

{summary}...

## 原始资料

- 来源: [[raw/{source.name}]]
- 字数: {len(body.split())}

## 详细内容

{body}

---

*由 NoteClaw Wiki 自动编译 | {datetime.now().isoformat()}*
"""
    
    def query(self, question: str) -> List[Dict]:
        """
        Query: 基于知识库回答问题
        
        搜索wiki中的相关页面，返回相关段落
        """
        results = []
        
        # 简单实现：全文搜索
        for wiki_file in self.wiki_dir.rglob('*.md'):
            try:
                content = wiki_file.read_text(encoding='utf-8')
                
                # 简单匹配
                if question.lower() in content.lower():
                    # 提取相关段落
                    lines = content.split('\n')
                    matches = []
                    for i, line in enumerate(lines):
                        if question.lower() in line.lower():
                            # 取前后3行
                            start = max(0, i-3)
                            end = min(len(lines), i+4)
                            matches.append('\n'.join(lines[start:end]))
                    
                    if matches:
                        results.append({
                            'file': str(wiki_file.relative_to(self.root)),
                            'title': wiki_file.stem,
                            'matches': matches[:3]  # 最多3个匹配
                        })
                        
            except Exception:
                continue
        
        return results
    
    def lint(self) -> Dict:
        """
        Lint: 检查健康度
        
        - 死链接（指向不存在的文件）
        - 孤立页面（没有被任何页面引用）
        - 覆盖缺口（概念缺失）
        """
        issues = {
            'dead_links': [],
            'orphans': [],
            'gaps': []
        }
        
        # 收集所有wiki页面
        all_pages = set()
        for f in self.wiki_dir.rglob('*.md'):
            if f.name != 'index.md':
                all_pages.add(f.stem)
        
        # 检查链接
        link_pattern = r'\[\[([^\]]+)\]\]'
        
        for wiki_file in self.wiki_dir.rglob('*.md'):
            try:
                content = wiki_file.read_text(encoding='utf-8')
                links = re.findall(link_pattern, content)
                
                for link in links:
                    link_name = link.strip()
                    if link_name not in all_pages and link_name + '.md' not in [f.name for f in self.wiki_dir.rglob('*.md')]:
                        issues['dead_links'].append({
                            'file': str(wiki_file.relative_to(self.root)),
                            'link': link_name
                        })
                        
            except Exception:
                continue
        
        # 检查孤立页面（没有入链）
        # 简化：假设index.md引用的就是有链接的
        if (self.wiki_dir / 'index.md').exists():
            index_content = (self.wiki_dir / 'index.md').read_text()
            linked = set(re.findall(link_pattern, index_content))
            
            for page in all_pages:
                if page not in linked and page + '.md' not in [f.name for f in self.wiki_dir.rglob('*.md')]:
                    issues['orphans'].append(page)
        
        self._log(f"lint | dead_links:{len(issues['dead_links'])} orphans:{len(issues['orphans'])}")
        
        return issues
    
    def audit(self) -> Dict:
        """
        Audit: 处理人类反馈
        
        读取audit目录的反馈文件，应用修正
        """
        resolved = []
        
        for audit_file in self.audit_dir.glob('*.md'):
            if audit_file.is_file() and audit_file.stem != 'resolved':
                try:
                    content = audit_file.read_text(encoding='utf-8')
                    
                    # 解析反馈
                    meta, body = self._parse_frontmatter(content)
                    target = meta.get('target', '')
                    correction = body
                    
                    # 应用修正（简化：追加到目标文件）
                    if target:
                        target_file = self.wiki_dir / target
                        if target_file.exists():
                            original = target_file.read_text()
                            updated = original + f"\n\n---\n\n## 人类反馈\n\n{correction}\n"
                            target_file.write_text(updated, encoding='utf-8')
                    
                    # 移动到resolved
                    resolved_file = self.resolved_dir / audit_file.name
                    audit_file.rename(resolved_file)
                    resolved.append(str(audit_file.name))
                    
                except Exception as e:
                    print(f"Audit error: {e}")
        
        self._log(f"audit | resolved:{len(resolved)}")
        
        return {'resolved': resolved}
    
    # ========== 辅助方法 ==========
    
    def _parse_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """解析YAML Frontmatter"""
        meta = {}
        body = content
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm = parts[1].strip()
                body = parts[2].strip()
                
                for line in fm.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        meta[key.strip()] = value.strip().strip('"').strip("'")
        
        return meta, body
    
    def _read_index(self) -> Dict:
        """读取index"""
        index_file = self.wiki_dir / 'index.md'
        if not index_file.exists():
            return {}
        
        content = index_file.read_text(encoding='utf-8')
        
        # 简单解析
        pages = {}
        current_category = None
        
        for line in content.split('\n'):
            if line.startswith('## '):
                current_category = line[3:].strip()
                pages[current_category] = []
            elif line.startswith('- '):
                link = line[2:].strip()
                if current_category:
                    pages[current_category].append(link)
        
        return pages
    
    def _rebuild_index(self):
        """重建index.md"""
        index_content = f"""---
title: NoteClaw Wiki Index
date: {datetime.now().isoformat()}
---

# 知识库索引

## 概念 (Concepts)

"""
        
        concepts_dir = self.wiki_dir / 'concepts'
        if concepts_dir.exists():
            for f in sorted(concepts_dir.rglob('*.md')):
                if f.name != 'index.md':
                    title = f.stem
                    index_content += f"- [[{title}]]\n"
        
        index_content += "\n## 实体 (Entities)\n\n"
        
        entities_dir = self.wiki_dir / 'entities'
        if entities_dir.exists():
            for f in sorted(entities_dir.rglob('*.md')):
                title = f.stem
                index_content += f"- [[{title}]]\n"
        
        (self.wiki_dir / 'index.md').write_text(index_content, encoding='utf-8')
        
        self._log("rebuild_index")
    
    def _log(self, message: str):
        """记录操作日志"""
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"{today}.md"
        
        time = datetime.now().strftime('%H:%M')
        entry = f"- [{time}] {message}\n"
        
        log_file.write_text(entry, encoding='utf-8')
    
    # ========== CLI 接口 ==========
    
    @staticmethod
    def cli():
        import argparse
        
        parser = argparse.ArgumentParser(description='NoteClaw Wiki')
        subparsers = parser.add_subparsers(dest='command')
        
        # ingest
        p_ingest = subparsers.add_parser('ingest', help='摄入原始资料')
        p_ingest.add_argument('source', help='源文件或URL')
        p_ingest.add_argument('--category', default='articles', help='分类')
        
        # compile
        p_compile = subparsers.add_parser('compile', help='编译wiki')
        p_compile.add_argument('--force', action='store_true', help='强制重新编译')
        
        # query
        p_query = subparsers.add_parser('query', help='查询')
        p_query.add_argument('question', help='问题')
        
        # lint
        p_lint = subparsers.add_parser('lint', help='检查健康度')
        
        # audit
        p_audit = subparsers.add_parser('audit', help='处理反馈')
        
        args = parser.parse_args()
        
        wiki = NoteClawWiki('.')
        
        if args.command == 'ingest':
            result = wiki.ingest(args.source, args.category)
            print(f"Ingested: {result}")
        
        elif args.command == 'compile':
            result = wiki.compile(args.force)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'query':
            result = wiki.query(args.question)
            for r in result:
                print(f"\n{r['title']}:")
                for m in r['matches']:
                    print(f"  {m[:100]}...")
        
        elif args.command == 'lint':
            result = wiki.lint()
            print(json.dumps(result, indent=2))
        
        elif args.command == 'audit':
            result = wiki.audit()
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    NoteClawWiki.cli()
