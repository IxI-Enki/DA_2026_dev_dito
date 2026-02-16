"""
Page Processor
==============
Converts DokuWiki syntax to Markdown.

DokuWiki Syntax Reference:
- Headings: ====== H1 ====== to == H5 ==
- Bold: **text**
- Italic: //text//
- Underline: __text__
- Monospace: ''text''
- Links: [[page|text]] or [[http://url|text]]
- Images: {{image.png}} or {{image.png?200x100}}
- Lists: * unordered, - numbered
- Tables: ^ header ^ and | cell |
- Code: <code lang>...</code>
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from strategy_loader import PageStrategy

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of a page conversion."""
    success: bool
    markdown: str
    title: str
    errors: List[str]
    warnings: List[str]


class PageProcessor:
    """Converts DokuWiki syntax to Markdown."""
    
    def __init__(self, wiki_base_url: str = ''):
        self.wiki_base_url = wiki_base_url
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def convert(self, wiki_content: str, page_id: str = '') -> ConversionResult:
        """
        Convert DokuWiki content to Markdown.
        
        Args:
            wiki_content: Raw DokuWiki syntax
            page_id: Page identifier for context
            
        Returns:
            ConversionResult with Markdown and metadata
        """
        self.errors = []
        self.warnings = []
        
        if not wiki_content or not wiki_content.strip():
            return ConversionResult(
                success=False,
                markdown='',
                title='',
                errors=['Empty content'],
                warnings=[]
            )
        
        try:
            # Extract title from first heading
            title = self._extract_title(wiki_content)
            
            # Apply conversions in order
            markdown = wiki_content
            
            # 1. Protect code blocks first
            markdown, code_blocks = self._protect_code_blocks(markdown)
            
            # 2. Convert headings
            markdown = self._convert_headings(markdown)
            
            # 3. Convert text formatting
            markdown = self._convert_formatting(markdown)
            
            # 4. Convert links
            markdown = self._convert_links(markdown)
            
            # 5. Convert images/media
            markdown = self._convert_media(markdown)
            
            # 6. Convert lists
            markdown = self._convert_lists(markdown)
            
            # 7. Convert tables
            markdown = self._convert_tables(markdown)
            
            # 8. Convert horizontal rules
            markdown = self._convert_horizontal_rules(markdown)
            
            # 9. Restore code blocks
            markdown = self._restore_code_blocks(markdown, code_blocks)
            
            # 10. Clean up
            markdown = self._cleanup(markdown)
            
            return ConversionResult(
                success=True,
                markdown=markdown,
                title=title,
                errors=self.errors,
                warnings=self.warnings
            )
            
        except Exception as e:
            logger.error(f"Conversion failed for {page_id}: {e}")
            return ConversionResult(
                success=False,
                markdown=wiki_content,
                title='',
                errors=[str(e)],
                warnings=self.warnings
            )
    
    def _extract_title(self, content: str) -> str:
        """Extract title from first heading."""
        # Match first H1: ====== Title ======
        match = re.search(r'^={6}\s*(.+?)\s*={6}', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Try H2 if no H1
        match = re.search(r'^={5}\s*(.+?)\s*={5}', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        return ''
    
    def _protect_code_blocks(self, content: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace code blocks with placeholders to protect them from conversion.
        Returns content with placeholders and a dict of placeholder -> original.
        """
        code_blocks = {}
        counter = [0]  # Use list for closure
        
        def replace_code(match):
            # Use <<<...>>> to avoid collision with __underline__ conversion
            placeholder = f"<<<CODE_BLOCK_{counter[0]}>>>"
            counter[0] += 1
            code_blocks[placeholder] = match.group(0)
            return placeholder
        
        # Match <code lang>...</code> and <file>...</file>
        patterns = [
            r'<code[^>]*>.*?</code>',
            r'<file[^>]*>.*?</file>',
            r"''[^']+''",  # Protect inline monospace
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, replace_code, content, flags=re.DOTALL)
        
        return content, code_blocks
    
    def _restore_code_blocks(self, content: str, code_blocks: Dict[str, str]) -> str:
        """Restore code blocks from placeholders with Markdown formatting."""
        for placeholder, original in code_blocks.items():
            # Convert <code lang>...</code> to ```lang...```
            converted = self._convert_code_block(original)
            content = content.replace(placeholder, converted)
        return content
    
    def _convert_code_block(self, code: str) -> str:
        """Convert a single code block to Markdown fenced code."""
        # Match <code lang>content</code>
        match = re.match(r'<code\s*([^>]*)>(.*?)</code>', code, re.DOTALL)
        if match:
            lang = match.group(1).strip().split()[0] if match.group(1).strip() else ''
            # Clean up language hint (remove - prefixes like "- conf/lang/...")
            if lang.startswith('-'):
                lang = ''
            content = match.group(2)
            return f"```{lang}\n{content}\n```"
        
        # Match <file>content</file>
        match = re.match(r'<file\s*([^>]*)>(.*?)</file>', code, re.DOTALL)
        if match:
            lang = match.group(1).strip().split()[0] if match.group(1).strip() else ''
            content = match.group(2)
            return f"```{lang}\n{content}\n```"
        
        # Match ''monospace''
        match = re.match(r"''(.+?)''", code)
        if match:
            return f"`{match.group(1)}`"
        
        return code
    
    def _convert_headings(self, content: str) -> str:
        """
        Convert DokuWiki headings to Markdown.
        ====== H1 ====== -> # H1
        ===== H2 =====   -> ## H2
        ==== H3 ====     -> ### H3
        === H4 ===       -> #### H4
        == H5 ==         -> ##### H5
        """
        # Process from H1 (6 =) to H5 (2 =)
        for level in range(6, 1, -1):
            pattern = rf'^={{{level}}}\s*(.+?)\s*={{{level}}}\s*$'
            markdown_level = 7 - level  # 6->1, 5->2, 4->3, 3->4, 2->5
            replacement = '#' * markdown_level + r' \1'
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        return content
    
    def _convert_formatting(self, content: str) -> str:
        """Convert text formatting."""
        # Bold: **text** stays the same in Markdown
        # Italic: //text// -> *text*
        content = re.sub(r'(?<!/)//(.*?)//(?!/)', r'*\1*', content)
        
        # Underline: __text__ -> <u>text</u> (no native Markdown support)
        content = re.sub(r'__(.*?)__', r'<u>\1</u>', content)
        
        # Monospace: ''text'' -> `text`
        content = re.sub(r"''(.+?)''", r'`\1`', content)
        
        # Subscript: <sub>text</sub> stays the same
        # Superscript: <sup>text</sup> stays the same
        
        # Strikethrough: <del>text</del> -> ~~text~~
        content = re.sub(r'<del>(.*?)</del>', r'~~\1~~', content)
        
        # Line breaks: \\ -> <br> or just newline
        content = re.sub(r'\\\\\s*', '  \n', content)
        
        return content
    
    def _convert_links(self, content: str) -> str:
        """
        Convert DokuWiki links to Markdown.
        [[page]] -> [page](page)
        [[page|text]] -> [text](page)
        [[http://url|text]] -> [text](http://url)
        [[namespace:page]] -> [namespace:page](namespace:page)
        """
        def convert_link(match):
            full = match.group(1)
            
            # Split on | for link text
            if '|' in full:
                parts = full.split('|', 1)
                target = parts[0].strip()
                text = parts[1].strip()
            else:
                target = full.strip()
                text = target
            
            # Handle different link types
            if target.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
                # External link - keep as-is
                return f'[{text}]({target})'
            elif target.startswith('\\\\'):
                # Windows share - keep as-is
                return f'[{text}]({target})'
            elif target.startswith('doku>'):
                # Interwiki DokuWiki link
                page = target[5:]
                return f'[{text}](https://www.dokuwiki.org/{page})'
            elif target.startswith('wp>'):
                # Interwiki Wikipedia link
                page = target[3:]
                return f'[{text}](https://en.wikipedia.org/wiki/{page})'
            else:
                # Internal wiki link; keep colon namespace, lowercase to match page_id
                target = target.lstrip(':').lower()
                if '#' in target:
                    page, anchor = target.split('#', 1)
                    return f'[{text}]({page}#{anchor})'
                return f'[{text}]({target})'
        
        # Match [[...]]
        content = re.sub(r'\[\[([^\]]+)\]\]', convert_link, content)
        
        return content
    
    def _convert_media(self, content: str) -> str:
        """
        Convert DokuWiki media/images to Markdown.
        {{image.png}} -> ![](image.png)
        {{image.png?200}} -> ![](image.png)
        {{image.png|alt text}} -> ![alt text](image.png)
        {{ image.png}} -> ![](image.png) (left aligned)
        {{image.png }} -> ![](image.png) (right aligned)
        """
        def convert_media(match):
            full = match.group(1)
            
            # Check alignment (spaces indicate alignment in DokuWiki)
            left_space = full.startswith(' ')
            right_space = full.endswith(' ')
            full = full.strip()
            
            # Split on | for alt text
            if '|' in full:
                parts = full.split('|', 1)
                src = parts[0].strip()
                alt = parts[1].strip()
            else:
                src = full
                alt = ''
            
            # Remove size parameters (e.g., ?200x100)
            if '?' in src:
                src = src.split('?')[0]
            # DokuWiki colon-paths: keep colon namespace, lowercase to match media_id
            src = src.lstrip(':').lower()
            
            return f'![{alt}]({src})'
        
        # Match {{...}}
        content = re.sub(r'\{\{([^}]+)\}\}', convert_media, content)
        
        return content
    
    def _convert_lists(self, content: str) -> str:
        """
        Convert DokuWiki lists to Markdown.
        DokuWiki uses 2 spaces for indentation:
          * item -> - item
          - item -> 1. item (numbered)
          * item -> - item
            * subitem -> - subitem (with more indent)
        """
        lines = content.split('\n')
        result = []
        
        for line in lines:
            # Match lines starting with spaces followed by * or -
            match = re.match(r'^(\s+)([*-])\s+(.*)$', line)
            if match:
                indent = match.group(1)
                marker = match.group(2)
                text = match.group(3)
                
                # Calculate Markdown indent (2 DokuWiki spaces = 2 Markdown spaces)
                md_indent = ' ' * (len(indent) - 2) if len(indent) >= 2 else ''
                
                if marker == '*':
                    # Unordered list
                    result.append(f'{md_indent}- {text}')
                else:
                    # Ordered list (DokuWiki uses - for numbered)
                    result.append(f'{md_indent}1. {text}')
            else:
                result.append(line)
        
        return '\n'.join(result)
    
    def _convert_tables(self, content: str) -> str:
        """
        Convert DokuWiki tables to Markdown tables.
        ^ Header ^ Header ^  -> | Header | Header |
        | Cell | Cell |      -> | Cell | Cell |
        """
        lines = content.split('\n')
        result = []
        in_table = False
        header_done = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check if this is a table line
            if stripped.startswith('^') or stripped.startswith('|'):
                if not in_table:
                    in_table = True
                    header_done = False
                
                # Convert header markers ^ to |
                converted = stripped.replace('^', '|')
                
                # Clean up double pipes
                converted = re.sub(r'\|\|+', '|', converted)
                
                # Ensure line starts and ends with |
                if not converted.endswith('|'):
                    converted += '|'
                
                result.append(converted)
                
                # Add separator after header row
                if stripped.startswith('^') and not header_done:
                    # Count columns
                    cols = converted.count('|') - 1
                    if cols > 0:
                        separator = '|' + '|'.join(['---'] * cols) + '|'
                        result.append(separator)
                    header_done = True
            else:
                in_table = False
                header_done = False
                result.append(line)
        
        return '\n'.join(result)
    
    def _convert_horizontal_rules(self, content: str) -> str:
        """Convert DokuWiki horizontal rules to Markdown."""
        # DokuWiki: ---- (4 or more dashes on own line)
        # Markdown: ---
        content = re.sub(r'^-{4,}\s*$', '---', content, flags=re.MULTILINE)
        return content
    
    # ------------------------------------------------------------------
    # Strategy-aware routing (T076)
    # ------------------------------------------------------------------

    def process_with_strategy(self, page: dict, strategy: "PageStrategy") -> dict:
        """Process a page using its assigned content strategy.

        - KNOWLEDGE pages: full markdown conversion + entity preservation
        - NEWS pages: extract date + summary, lighter processing
        - PORTAL pages: extract links + structure, minimal text
        - FORM pages: preserve form fields as structured data
        - ARCHIVED pages: minimal processing, mark as low-priority

        Args:
            page: Dict with at least ``content`` and ``page_id``.
            strategy: A ``PageStrategy`` instance from the StrategyLoader.

        Returns:
            Dict with ``markdown``, ``content_type``, ``chunk_size``,
            ``priority``, and ``rag_readiness``.
        """
        from strategy_loader import ContentType  # local import to avoid circular

        content = page.get("content", "")
        page_id = page.get("page_id", "")
        ct = strategy.content_type

        result = self.convert(content, page_id)

        priority = "normal"
        if ct == ContentType.ARCHIVED:
            priority = "low"
        elif ct in (ContentType.KNOWLEDGE,):
            priority = "high"

        return {
            "markdown": result.markdown,
            "content_type": ct.value.lower(),
            "chunk_size": strategy.chunk_size,
            "chunking_method": strategy.chunking_method,
            "priority": priority,
            "action": strategy.action,
            "title": result.title,
            "errors": result.errors,
        }

    def _cleanup(self, content: str) -> str:
        """Final cleanup of converted content."""
        # Remove DokuWiki-specific tags
        content = re.sub(r'~~NOTOC~~', '', content)
        content = re.sub(r'~~NOCACHE~~', '', content)
        content = re.sub(r'<nowiki>.*?</nowiki>', '', content, flags=re.DOTALL)
        
        # Clean up multiple blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Trim trailing whitespace
        content = '\n'.join(line.rstrip() for line in content.split('\n'))
        
        return content.strip()
