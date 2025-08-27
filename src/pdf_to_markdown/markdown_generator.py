import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generate well-formatted Markdown from extracted content"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.image_format = self.config.get('image_format', 'relative')  # relative, absolute, embedded
        self.code_fence_style = self.config.get('code_fence_style', 'backticks')  # backticks, tildes
        self.table_alignment = self.config.get('table_alignment', 'left')  # left, center, right
        self.heading_style = self.config.get('heading_style', 'atx')  # atx (#), setext (underline)
        self.link_style = self.config.get('link_style', 'inline')  # inline, reference
        self.max_line_length = self.config.get('max_line_length', 100)
        
    def generate_document(self, document_node: Any, output_dir: Path, 
                         image_paths: Dict[Any, Path] = None,
                         table_paths: Dict[Any, Dict[str, Path]] = None,
                         code_paths: Dict[Any, Path] = None,
                         output_filename: str = None) -> Path:
        """Generate complete Markdown document from document structure"""
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate markdown for each section
        self._generate_section_files(document_node, output_dir, image_paths, table_paths, code_paths)
        
        # Generate main index/README
        index_path = self._generate_index(document_node, output_dir, output_filename)
        
        return index_path
    
    def _generate_section_files(self, node: Any, output_dir: Path,
                               image_paths: Dict[Any, Path] = None,
                               table_paths: Dict[Any, Dict[str, Path]] = None,
                               code_paths: Dict[Any, Path] = None,
                               level: int = 0):
        """Generate Markdown files for each section"""
        
        # Skip root node
        if hasattr(node, 'node_type') and node.node_type == 'root':
            for child in node.children:
                self._generate_section_files(child, output_dir, image_paths, table_paths, code_paths, level)
            return
            
        # Create folder for this section
        section_dir = output_dir / node.slug if hasattr(node, 'slug') else output_dir
        section_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate markdown content
        content = []
        
        # Add heading
        heading = self._format_heading(node.title, level + 1)
        content.append(heading)
        content.append("")  # Empty line after heading
        
        # Add metadata
        if hasattr(node, 'page_start') and node.page_start:
            content.append(f"*Pages: {node.page_start}-{node.page_end or node.page_start}*")
            content.append("")
            
        # Process content blocks
        for block in node.content:
            block_type = type(block).__name__
            
            if hasattr(block, 'block_type'):
                # Text block
                if block.block_type in ['paragraph', 'text']:
                    content.append(self._format_paragraph(block.content))
                    content.append("")
                elif block.block_type == 'list':
                    content.append(self._format_list(block.content))
                    content.append("")
                elif block.block_type.startswith('heading'):
                    level_num = int(block.block_type[-1]) if block.block_type[-1].isdigit() else 3
                    content.append(self._format_heading(block.content, level_num))
                    content.append("")
                    
            elif block_type == 'ExtractedImage' and image_paths:
                # Image
                img_path = image_paths.get(block)
                if img_path:
                    img_md = self._format_image(img_path, section_dir, block)
                    content.append(img_md)
                    content.append("")
                    
            elif block_type == 'ExtractedTable' and table_paths:
                # Table
                paths = table_paths.get(block, {})
                if 'markdown' in paths:
                    table_content = paths['markdown'].read_text(encoding='utf-8')
                    content.append(table_content)
                else:
                    table_md = self._format_table(block)
                    content.append(table_md)
                content.append("")
                
            elif block_type == 'CodeBlock' and code_paths:
                # Code block
                code_path = code_paths.get(block)
                code_md = self._format_code_block(block, code_path, section_dir)
                content.append(code_md)
                content.append("")
                
        # Process child sections
        if node.children:
            content.append("")
            content.append("## Subsections")
            content.append("")
            
            for child in node.children:
                # Create link to child section
                child_file = f"{child.slug}/index.md"
                content.append(f"- [{child.title}]({child_file})")
                
                # Generate child section file
                self._generate_section_files(child, section_dir, image_paths, table_paths, code_paths, level + 1)
                
        # Write section file
        section_file = section_dir / "index.md"
        section_file.write_text('\n'.join(content), encoding='utf-8')
        logger.info(f"Generated section file: {section_file}")
    
    def _generate_index(self, root_node: Any, output_dir: Path, output_filename: str = None) -> Path:
        """Generate main index/README file"""
        content = []
        
        # Title
        content.append("# Document Index")
        content.append("")
        
        # Add root content if it exists (for documents without sections)
        if hasattr(root_node, 'content') and root_node.content:
            content.append("## Document Content")
            content.append("")
            for block in root_node.content:
                if hasattr(block, 'block_type'):
                    if block.block_type in ['paragraph', 'text']:
                        content.append(self._format_paragraph(block.content))
                        content.append("")
                    elif block.block_type == 'list':
                        content.append(self._format_list(block.content))
                        content.append("")
            content.append("")
        
        # Generate table of contents only if there are children
        if hasattr(root_node, 'children') and root_node.children:
            content.append("## Table of Contents")
            content.append("")
            
            def generate_toc(node: Any, indent: int = 0):
                if hasattr(node, 'node_type') and node.node_type == 'root':
                    for child in node.children:
                        generate_toc(child, indent)
                else:
                    # Create link
                    link_path = f"{node.slug}/index.md"
                    indent_str = "  " * indent
                    content.append(f"{indent_str}- [{node.title}]({link_path})")
                    
                    # Add children
                    for child in node.children:
                        generate_toc(child, indent + 1)
                        
            generate_toc(root_node)
            content.append("")
        
        # Add document statistics
        content.append("")
        content.append("## Document Statistics")
        content.append("")
        
        stats = self._calculate_statistics(root_node)
        content.append(f"- Total sections: {stats['sections']}")
        content.append(f"- Total pages: {stats['pages']}")
        content.append(f"- Images: {stats['images']}")
        content.append(f"- Tables: {stats['tables']}")
        content.append(f"- Code blocks: {stats['code_blocks']}")
        
        # Write index file - use PDF filename if provided, otherwise README.md
        if output_filename:
            index_file = output_dir / f"{output_filename}.md"
        else:
            index_file = output_dir / "README.md"
        
        index_file.write_text('\n'.join(content), encoding='utf-8')
        
        logger.info(f"Generated index file: {index_file}")
        return index_file
    
    def _format_heading(self, text: str, level: int) -> str:
        """Format heading in Markdown"""
        if self.heading_style == 'atx':
            return f"{'#' * min(level, 6)} {text}"
        else:  # setext style for levels 1 and 2
            if level == 1:
                return f"{text}\n{'=' * len(text)}"
            elif level == 2:
                return f"{text}\n{'-' * len(text)}"
            else:
                return f"{'#' * level} {text}"
    
    def _format_paragraph(self, text: str) -> str:
        """Format paragraph with line wrapping"""
        if not text:
            return ""
            
        # Clean up text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Wrap lines if needed
        if self.max_line_length and len(text) > self.max_line_length:
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                word_length = len(word)
                if current_length + word_length + 1 <= self.max_line_length:
                    current_line.append(word)
                    current_length += word_length + 1
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = word_length
                    
            if current_line:
                lines.append(' '.join(current_line))
                
            return '\n'.join(lines)
        else:
            return text
    
    def _format_list(self, text: str) -> str:
        """Format list items"""
        lines = text.split('\n')
        formatted = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Detect if ordered or unordered
                if re.match(r'^\d+[\.\)]\s*', line):
                    # Already numbered
                    formatted.append(line)
                elif re.match(r'^[\-\*\•]\s*', line):
                    # Already bulleted
                    formatted.append(line)
                else:
                    # Add bullet
                    formatted.append(f"- {line}")
                    
        return '\n'.join(formatted)
    
    def _format_image(self, img_path: Path, base_dir: Path, image_obj: Any) -> str:
        """Format image reference in Markdown"""
        # Calculate relative path
        try:
            rel_path = img_path.relative_to(base_dir)
        except ValueError:
            rel_path = img_path
            
        # Get alt text
        alt_text = getattr(image_obj, 'alt_text', None) or getattr(image_obj, 'caption', None) or "Image"
        
        # Format based on style
        if self.image_format == 'embedded':
            # Embed as base64 (not implemented for brevity)
            return f"![{alt_text}]({rel_path})"
        else:
            return f"![{alt_text}]({rel_path})"
    
    def _format_table(self, table_obj: Any) -> str:
        """Format table in Markdown"""
        if not hasattr(table_obj, 'data'):
            return ""
            
        df = table_obj.data
        lines = []
        
        # Caption
        if hasattr(table_obj, 'caption') and table_obj.caption:
            lines.append(f"**{table_obj.caption}**")
            lines.append("")
            
        # Headers
        headers = list(df.columns)
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        lines.append(header_row)
        
        # Alignment row
        if self.table_alignment == 'center':
            align = "|" + "|".join([" :---: " for _ in headers]) + "|"
        elif self.table_alignment == 'right':
            align = "|" + "|".join([" ---: " for _ in headers]) + "|"
        else:
            align = "|" + "|".join([" --- " for _ in headers]) + "|"
        lines.append(align)
        
        # Data rows
        for _, row in df.iterrows():
            row_str = "| " + " | ".join(str(val) for val in row) + " |"
            lines.append(row_str)
            
        return '\n'.join(lines)
    
    def _format_code_block(self, code_obj: Any, code_path: Optional[Path], base_dir: Path) -> str:
        """Format code block in Markdown"""
        language = getattr(code_obj, 'language', '') or ''
        content = getattr(code_obj, 'content', '')
        
        if self.code_fence_style == 'tildes':
            fence = "~~~"
        else:
            fence = "```"
            
        lines = [f"{fence}{language}"]
        lines.append(content)
        lines.append(fence)
        
        # Add link to file if saved
        if code_path:
            try:
                rel_path = code_path.relative_to(base_dir)
                lines.append(f"*[View full code]({rel_path})*")
            except ValueError:
                pass
                
        return '\n'.join(lines)
    
    def _calculate_statistics(self, root_node: Any) -> Dict[str, int]:
        """Calculate document statistics"""
        stats = {
            'sections': 0,
            'pages': 0,
            'images': 0,
            'tables': 0,
            'code_blocks': 0
        }
        
        def count_node(node: Any):
            if hasattr(node, 'node_type') and node.node_type != 'root':
                stats['sections'] += 1
                
            if hasattr(node, 'page_end'):
                stats['pages'] = max(stats['pages'], node.page_end or 0)
                
            for item in getattr(node, 'content', []):
                item_type = type(item).__name__
                if item_type == 'ExtractedImage':
                    stats['images'] += 1
                elif item_type == 'ExtractedTable':
                    stats['tables'] += 1
                elif item_type == 'CodeBlock':
                    stats['code_blocks'] += 1
                    
            for child in getattr(node, 'children', []):
                count_node(child)
                
        count_node(root_node)
        return stats