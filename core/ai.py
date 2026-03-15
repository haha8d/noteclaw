#!/usr/bin/env python3
"""
NoteClaw AI 接口 - 智能抓取和提炼
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# 可选依赖
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent))
from core import NoteClawCore

NOTECLAW_DIR = Path(os.environ.get('NOTECLAW_DIR', Path.home() / '.noteclaw'))

class NoteClawAI:
    """NoteClaw AI 功能"""
    
    def __init__(self, root_dir: str = None):
        self.root = Path(root_dir) if root_dir else NOTECLAW_DIR
        self.core = NoteClawCore(self.root)
    
    def fetch_url(self, url: str, save: bool = True, category: str = "references") -> dict:
        """
        抓取网页内容并转换为 Markdown
        
        Args:
            url: 要抓取的URL
            save: 是否保存到笔记
            category: 保存分类
        
        Returns:
            {
                'title': '页面标题',
                'content': 'Markdown内容',
                'url': '原始URL',
                'path': '保存路径（如果save=True）'
            }
        """
        if not REQUESTS_AVAILABLE:
            return {'error': '需要安装 requests: pip install requests'}
        
        try:
            # 抓取页面
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = response.apparent_encoding
            
            # 解析HTML
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取标题
                title = soup.find('title')
                title = title.get_text().strip() if title else 'Untitled'
                
                # 提取正文（优先选择article或main）
                article = soup.find('article') or soup.find('main') or soup.find('body')
                
                # 转换为Markdown
                content = self._html_to_markdown(article)
            else:
                # 简单提取
                title = 'Untitled'
                content = response.text[:5000]
            
            result = {
                'title': title,
                'content': content,
                'url': url,
                'fetched_at': datetime.now().isoformat()
            }
            
            # 保存到笔记
            if save:
                path = self._save_fetched_content(result, category)
                result['path'] = path
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def _html_to_markdown(self, element) -> str:
        """将HTML元素转换为Markdown"""
        if not element:
            return ''
        
        md_parts = []
        
        for tag in element.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'pre', 'blockquote']):
            text = tag.get_text().strip()
            if not text:
                continue
            
            if tag.name == 'h1':
                md_parts.append(f'# {text}')
            elif tag.name == 'h2':
                md_parts.append(f'## {text}')
            elif tag.name == 'h3':
                md_parts.append(f'### {text}')
            elif tag.name == 'h4':
                md_parts.append(f'#### {text}')
            elif tag.name == 'p':
                md_parts.append(text)
            elif tag.name == 'blockquote':
                md_parts.append(f'> {text}')
            elif tag.name in ['ul', 'ol']:
                for li in tag.find_all('li'):
                    li_text = li.get_text().strip()
                    if tag.name == 'ul':
                        md_parts.append(f'- {li_text}')
                    else:
                        md_parts.append(f'1. {li_text}')
            elif tag.name == 'pre':
                code = tag.get_text()
                md_parts.append(f'```\n{code}\n```')
        
        return '\n\n'.join(md_parts)
    
    def _save_fetched_content(self, result: dict, category: str) -> str:
        """保存抓取的内容到笔记"""
        date = datetime.now().strftime('%Y-%m-%d')
        domain = urlparse(result['url']).netloc.replace('.', '_')
        safe_title = re.sub(r'[^\w\s-]', '', result['title'])[:50]
        filename = f"{date}_{domain}_{safe_title.replace(' ', '_')}.md"
        
        filepath = self.root / 'topics' / category / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        content = f"""---
title: {result['title']}
created: {date}
source: {result['url']}
tags: [fetched, web]
category: {category}
---

# {result['title']}

> 原文链接: [{result['url']}]({result['url']})
> 抓取时间: {result['fetched_at']}

## 内容

{result['content']}

---

*本内容由 NoteClaw 自动抓取*
"""
        
        filepath.write_text(content, encoding='utf-8')
        
        # 索引
        self.core.index_note(str(filepath))
        
        return str(filepath.relative_to(self.root))
    
    def distill(self, text: str, mode: str = 'summary', save: bool = False, title: str = None) -> dict:
        """
        提炼长文本
        
        Args:
            text: 要提炼的长文本
            mode: 提炼模式
                - 'summary': 生成摘要
                - 'keypoints': 提取关键点
                - 'outline': 生成大纲
                - 'qa': 生成问答形式
                - 'mindmap': 生成思维导图格式
            save: 是否保存结果
            title: 保存时的标题
        
        Returns:
            {
                'mode': '提炼模式',
                'result': '提炼结果',
                'path': '保存路径（如果save=True）'
            }
        """
        if mode == 'summary':
            result = self._distill_summary(text)
        elif mode == 'keypoints':
            result = self._distill_keypoints(text)
        elif mode == 'outline':
            result = self._distill_outline(text)
        elif mode == 'qa':
            result = self._distill_qa(text)
        elif mode == 'mindmap':
            result = self._distill_mindmap(text)
        else:
            result = self._distill_summary(text)
        
        output = {
            'mode': mode,
            'result': result,
            'original_length': len(text),
            'result_length': len(result)
        }
        
        if save:
            path = self._save_distilled_content(output, title or f"提炼_{mode}")
            output['path'] = path
        
        return output
    
    def _distill_summary(self, text: str) -> str:
        """生成摘要 - 提取关键句子"""
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # 简单策略：取前3句和包含关键词的句子
        keywords = self._extract_keywords(text)
        important = []
        
        for sent in sentences[:10]:  # 只看前10句
            if any(kw in sent for kw in keywords[:5]):
                important.append(sent)
        
        # 如果没有重要句子，取前3句
        if not important and sentences:
            important = sentences[:3]
        
        return '\n\n'.join(important[:5])  # 最多5句
    
    def _distill_keypoints(self, text: str) -> str:
        """提取关键点"""
        lines = text.split('\n')
        keypoints = []
        
        for line in lines:
            line = line.strip()
            # 识别列表项
            if re.match(r'^[\d\-\*•]\s+', line):
                keypoints.append(line)
            # 识别粗体/强调
            elif '**' in line or '__' in line:
                keypoints.append(line)
            # 识别标题
            elif line.startswith('#'):
                keypoints.append(line)
        
        if not keypoints:
            # 如果没有明显的关键点，生成一些
            return self._distill_summary(text)
        
        return '\n'.join([f'- {kp}' for kp in keypoints[:10]])
    
    def _distill_outline(self, text: str) -> str:
        """生成大纲"""
        lines = text.split('\n')
        outline = []
        level = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 识别标题层级
            if line.startswith('# '):
                outline.append(f"# {line[2:]}")
                level = 1
            elif line.startswith('## '):
                outline.append(f"## {line[3:]}")
                level = 2
            elif line.startswith('### '):
                outline.append(f"### {line[4:]}")
                level = 3
            elif line.startswith('#### '):
                outline.append(f"#### {line[5:]}")
                level = 4
            elif level > 0 and len(line) < 100:
                # 可能是子项
                outline.append(f"{'  ' * level}- {line}")
        
        return '\n'.join(outline) if outline else self._distill_summary(text)
    
    def _distill_qa(self, text: str) -> str:
        """生成问答形式"""
        # 识别问题模式
        questions = []
        
        # 找包含问号的句子
        q_sentences = re.findall(r'[^。！？]*[？\?][^。！？]*[。！？]?', text)
        
        if q_sentences:
            for q in q_sentences[:5]:
                q = q.strip()
                # 找答案（后面的句子）
                idx = text.find(q)
                if idx >= 0:
                    after = text[idx + len(q):idx + len(q) + 200]
                    answer = after.split('。')[0] if '。' in after else after[:100]
                    questions.append(f"**Q: {q}**\nA: {answer}...")
        
        if not questions:
            # 生成通用问答
            keywords = self._extract_keywords(text)[:3]
            for kw in keywords:
                idx = text.find(kw)
                if idx >= 0:
                    context = text[max(0, idx-50):idx+150]
                    questions.append(f"**Q: 什么是{kw}？**\nA: {context}...")
        
        return '\n\n'.join(questions[:5])
    
    def _distill_mindmap(self, text: str) -> str:
        """生成思维导图格式（Markdown 列表）"""
        lines = text.split('\n')
        mindmap = ['# 思维导图']
        current_branch = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('# '):
                mindmap.append(f"\n## {line[2:]}")
                current_branch = None
            elif line.startswith('## '):
                mindmap.append(f"- {line[3:]}")
                current_branch = line[3:]
            elif line.startswith('### '):
                mindmap.append(f"  - {line[4:]}")
            elif line.startswith('#### '):
                mindmap.append(f"    - {line[5:]}")
            elif current_branch and len(line) < 50 and not line.startswith('-'):
                mindmap.append(f"  - {line}")
        
        return '\n'.join(mindmap) if len(mindmap) > 1 else self._distill_outline(text)
    
    def _extract_keywords(self, text: str) -> list:
        """提取关键词（简单实现）"""
        # 统计词频（中文）
        words = re.findall(r'[\u4e00-\u9fa5]{2,8}', text)
        word_freq = {}
        for w in words:
            if len(w) >= 2:
                word_freq[w] = word_freq.get(w, 0) + 1
        
        # 排序返回
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, f in sorted_words[:10]]
    
    def _save_distilled_content(self, output: dict, title: str) -> str:
        """保存提炼结果"""
        date = datetime.now().strftime('%Y-%m-%d')
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        filename = f"{date}_{safe_title.replace(' ', '_')}.md"
        
        filepath = self.root / 'topics' / 'references' / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        content = f"""---
title: {title}
created: {date}
tags: [distilled, ai]
category: references
distill_mode: {output['mode']}
original_length: {output['original_length']}
result_length: {output['result_length']}
compression_ratio: {output['result_length'] / output['original_length']:.1%}
---

# {title}

> 提炼模式: {output['mode']}
> 原文长度: {output['original_length']} 字符
> 结果长度: {output['result_length']} 字符
> 压缩率: {output['result_length'] / output['original_length']:.1%}

## 提炼内容

{output['result']}

---

*本内容由 NoteClaw AI 自动提炼*
"""
        
        filepath.write_text(content, encoding='utf-8')
        
        # 索引
        self.core.index_note(str(filepath))
        
        return str(filepath.relative_to(self.root))
    
    def close(self):
        self.core.close()


# CLI 接口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='NoteClaw AI 工具')
    subparsers = parser.add_subparsers(dest='command')
    
    # fetch 命令
    p_fetch = subparsers.add_parser('fetch', help='抓取网页')
    p_fetch.add_argument('url', help='网页URL')
    p_fetch.add_argument('--no-save', action='store_true', help='不保存到笔记')
    p_fetch.add_argument('--category', default='references', help='保存分类')
    
    # distill 命令
    p_distill = subparsers.add_parser('distill', help='提炼文本')
    p_distill.add_argument('file', help='文本文件路径')
    p_distill.add_argument('--mode', default='summary', 
                          choices=['summary', 'keypoints', 'outline', 'qa', 'mindmap'],
                          help='提炼模式')
    p_distill.add_argument('--save', action='store_true', help='保存结果')
    p_distill.add_argument('--title', help='保存标题')
    
    args = parser.parse_args()
    
    ai = NoteClawAI()
    
    if args.command == 'fetch':
        result = ai.fetch_url(args.url, save=not args.no_save, category=args.category)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == 'distill':
        text = Path(args.file).read_text(encoding='utf-8')
        result = ai.distill(text, mode=args.mode, save=args.save, title=args.title)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    ai.close()
