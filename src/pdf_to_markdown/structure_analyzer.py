import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import re
from pathlib import Path
from slugify import slugify
from pdf_to_markdown.extractors.content_merger import ContentMerger, ContentBlock

logger = logging.getLogger(__name__)


@dataclass
class DocumentNode:
    """Represents a node in the document hierarchy"""
    title: str
    level: int  # 0 = root, 1 = chapter, 2 = section, etc.
    content: List[Any] = field(default_factory=list)
    children: List['DocumentNode'] = field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    node_type: str = "section"  # section, chapter, appendix, etc.
    slug: Optional[str] = None
    
    def __post_init__(self):
        if not self.slug:
            self.slug = slugify(self.title)


class DocumentStructureAnalyzer:
    """Analyze and build document structure hierarchy"""
    
    def __init__(self):
        self.toc_patterns = [
            re.compile(r'^(Chapter|CHAPTER)\s+(\d+|[IVX]+)[\s:\-]*(.+)', re.IGNORECASE),
            re.compile(r'^(\d+)\.?\s+(.+)'),
            re.compile(r'^(\d+\.\d+)\.?\s+(.+)'),
            re.compile(r'^([A-Z])\.?\s+(.+)'),
            re.compile(r'^(Section|SECTION)\s+(\d+|[IVX]+)[\s:\-]*(.+)', re.IGNORECASE),
            re.compile(r'^(Part|PART)\s+(\d+|[IVX]+)[\s:\-]*(.+)', re.IGNORECASE),
            re.compile(r'^(Appendix|APPENDIX)\s+([A-Z])[\s:\-]*(.+)', re.IGNORECASE),
        ]
        
    def analyze(self, text_blocks: List[Any], images: List[Any] = None, 
                tables: List[Any] = None, code_blocks: List[Any] = None) -> DocumentNode:
        """Build complete document structure"""
        
        # Create root node
        root = DocumentNode("Document", level=0, node_type="root")
        
        # Merge content in reading order
        content_merger = ContentMerger()
        merged_content = content_merger.merge_content(text_blocks, images, tables)
        
        # Detect table of contents if present
        toc = self._detect_table_of_contents(text_blocks)
        
        # Build hierarchy from headings
        hierarchy = self._build_hierarchy_from_headings(text_blocks)
        
        # Merge TOC and heading hierarchy
        if toc:
            hierarchy = self._merge_with_toc(hierarchy, toc)
            
        # If no hierarchy was found, put merged content directly in root
        if not hierarchy:
            # Assign merged content directly to root in reading order
            root.content = merged_content
            # Add code blocks separately as they're detected from text
            for code in (code_blocks or []):
                root.content.append(code)
        else:
            # Assign merged content to sections
            self._assign_merged_content_to_sections(hierarchy, merged_content, code_blocks)
            # Optimize structure
            hierarchy = self._optimize_structure(hierarchy)
            root.children = hierarchy
        
        return root
    
    def _detect_table_of_contents(self, text_blocks: List[Any]) -> Optional[List[Dict[str, Any]]]:
        """Detect and parse table of contents"""
        toc = []
        toc_started = False
        toc_page_limit = 10  # TOC usually in first few pages
        
        for block in text_blocks:
            if hasattr(block, 'page_num') and block.page_num > toc_page_limit:
                break
                
            content = getattr(block, 'content', '')
            
            # Check for TOC indicators
            if re.search(r'table of contents|contents|index', content, re.IGNORECASE):
                toc_started = True
                continue
                
            if toc_started:
                # Parse TOC entries
                for pattern in self.toc_patterns:
                    match = pattern.match(content.strip())
                    if match:
                        groups = match.groups()
                        if len(groups) >= 2:
                            toc.append({
                                'title': groups[-1].strip(),
                                'number': groups[0] if len(groups) > 2 else None,
                                'page': self._extract_page_number(content)
                            })
                            break
                            
                # Stop if we hit non-TOC content
                if content.strip() and not any(pattern.match(content.strip()) for pattern in self.toc_patterns):
                    if len(toc) > 3:  # Valid TOC found
                        break
                    else:
                        toc = []  # False positive, reset
                        toc_started = False
                        
        return toc if len(toc) > 3 else None
    
    def _build_hierarchy_from_headings(self, text_blocks: List[Any]) -> List[DocumentNode]:
        """Build document hierarchy from detected headings"""
        nodes = []
        current_level_nodes = {0: nodes}
        
        for block in text_blocks:
            block_type = getattr(block, 'block_type', 'paragraph')
            
            if block_type.startswith('heading'):
                # Determine heading level
                level = int(block_type[-1]) if block_type[-1].isdigit() else 2
                content = getattr(block, 'content', '').strip()
                page_num = getattr(block, 'page_num', None)
                
                # Create node
                node = DocumentNode(
                    title=content,
                    level=level,
                    page_start=page_num,
                    node_type=self._classify_section_type(content)
                )
                
                # Find parent level
                parent_level = level - 1
                while parent_level >= 0 and parent_level not in current_level_nodes:
                    parent_level -= 1
                    
                if parent_level >= 0 and current_level_nodes[parent_level]:
                    # Add to last node at parent level
                    parent = current_level_nodes[parent_level][-1] if isinstance(current_level_nodes[parent_level], list) else current_level_nodes[parent_level]
                    if isinstance(parent, DocumentNode):
                        parent.children.append(node)
                    else:
                        parent.append(node)
                else:
                    # Add to root level
                    nodes.append(node)
                    
                # Update current level tracking
                if level not in current_level_nodes:
                    current_level_nodes[level] = []
                current_level_nodes[level].append(node)
                
        return nodes
    
    def _merge_with_toc(self, hierarchy: List[DocumentNode], toc: List[Dict[str, Any]]) -> List[DocumentNode]:
        """Merge detected hierarchy with TOC information"""
        # Match TOC entries with hierarchy nodes
        for toc_entry in toc:
            title = toc_entry['title']
            page = toc_entry.get('page')
            
            # Find matching node in hierarchy
            node = self._find_node_by_title(hierarchy, title)
            if node and page:
                node.page_start = page
                
        return hierarchy
    
    def _assign_merged_content_to_sections(self, hierarchy: List[DocumentNode], 
                                          merged_content: List[ContentBlock],
                                          code_blocks: List[Any] = None):
        """Assign merged content blocks to appropriate sections"""
        all_nodes = self._flatten_hierarchy(hierarchy)
        
        # Sort nodes by page start
        all_nodes.sort(key=lambda n: n.page_start or 0)
        
        # Assign merged content blocks
        for block in merged_content:
            # Skip heading text blocks as they define structure
            if block.content_type == 'text' and hasattr(block.content, 'block_type'):
                if block.content.block_type.startswith('heading'):
                    continue
                    
            page_num = block.page_num
            node = self._find_section_for_page(all_nodes, page_num)
            if node:
                node.content.append(block)
            elif hierarchy:
                # Add to first section if no matching page found
                hierarchy[0].content.append(block) 
                
        # Add code blocks
        if code_blocks:
            for code in code_blocks:
                page_num = getattr(code, 'page_num', 0)
                node = self._find_section_for_page(all_nodes, page_num)
                if node:
                    node.content.append(code)
    
    def _assign_content_to_sections(self, hierarchy: List[DocumentNode], text_blocks: List[Any],
                                   images: List[Any] = None, tables: List[Any] = None,
                                   code_blocks: List[Any] = None):
        """Assign content blocks to appropriate sections"""
        all_nodes = self._flatten_hierarchy(hierarchy)
        
        # Sort nodes by page start
        all_nodes.sort(key=lambda n: n.page_start or 0)
        
        # Assign text blocks
        for block in text_blocks:
            block_type = getattr(block, 'block_type', 'paragraph')
            if not block_type.startswith('heading'):
                page_num = getattr(block, 'page_num', 0)
                node = self._find_section_for_page(all_nodes, page_num)
                if node:
                    node.content.append(block)
                elif not all_nodes and hierarchy:
                    # If no sections exist, add to root
                    hierarchy[0].content.append(block) if hierarchy else None
                    
        # Assign images
        if images:
            for img in images:
                page_num = getattr(img, 'page_num', 0)
                node = self._find_section_for_page(all_nodes, page_num)
                if node:
                    node.content.append(img)
                    
        # Assign tables
        if tables:
            for table in tables:
                page_num = getattr(table, 'page_num', 0)
                node = self._find_section_for_page(all_nodes, page_num)
                if node:
                    node.content.append(table)
                    
        # Assign code blocks
        if code_blocks:
            for code in code_blocks:
                page_num = getattr(code, 'page_num', 0)
                node = self._find_section_for_page(all_nodes, page_num)
                if node:
                    node.content.append(code)
    
    def _optimize_structure(self, hierarchy: List[DocumentNode]) -> List[DocumentNode]:
        """Optimize document structure for better organization"""
        # Remove empty sections
        hierarchy = self._remove_empty_sections(hierarchy)
        
        # Merge single-child sections
        hierarchy = self._merge_single_child_sections(hierarchy)
        
        # Balance deep hierarchies
        hierarchy = self._balance_hierarchy(hierarchy)
        
        return hierarchy
    
    def _remove_empty_sections(self, nodes: List[DocumentNode]) -> List[DocumentNode]:
        """Remove sections with no content"""
        filtered = []
        for node in nodes:
            if node.content or node.children:
                if node.children:
                    node.children = self._remove_empty_sections(node.children)
                filtered.append(node)
        return filtered
    
    def _merge_single_child_sections(self, nodes: List[DocumentNode]) -> List[DocumentNode]:
        """Merge sections that only have one child"""
        optimized = []
        for node in nodes:
            if len(node.children) == 1 and not node.content:
                # Merge with single child
                child = node.children[0]
                child.title = f"{node.title} - {child.title}"
                if node.children:
                    child.children = self._merge_single_child_sections(child.children)
                optimized.append(child)
            else:
                if node.children:
                    node.children = self._merge_single_child_sections(node.children)
                optimized.append(node)
        return optimized
    
    def _balance_hierarchy(self, nodes: List[DocumentNode], max_depth: int = 4) -> List[DocumentNode]:
        """Balance hierarchy to avoid too deep nesting"""
        def flatten_deep_nodes(node: DocumentNode, current_depth: int = 0):
            if current_depth >= max_depth and node.children:
                # Flatten children into content
                for child in node.children:
                    node.content.extend(child.content)
                    if child.children:
                        node.content.extend(flatten_deep_nodes(child, current_depth + 1).content)
                node.children = []
            else:
                node.children = [flatten_deep_nodes(child, current_depth + 1) for child in node.children]
            return node
            
        return [flatten_deep_nodes(node, 1) for node in nodes]
    
    def _classify_section_type(self, title: str) -> str:
        """Classify section type based on title"""
        title_lower = title.lower()
        
        if re.search(r'chapter|chapitre', title_lower):
            return "chapter"
        elif re.search(r'appendix|annexe', title_lower):
            return "appendix"
        elif re.search(r'part|partie', title_lower):
            return "part"
        elif re.search(r'introduction|preface|foreword', title_lower):
            return "introduction"
        elif re.search(r'conclusion|summary|epilogue', title_lower):
            return "conclusion"
        elif re.search(r'bibliography|references|works cited', title_lower):
            return "bibliography"
        elif re.search(r'glossary|definitions', title_lower):
            return "glossary"
        elif re.search(r'index', title_lower):
            return "index"
        else:
            return "section"
    
    def _extract_page_number(self, text: str) -> Optional[int]:
        """Extract page number from TOC entry"""
        # Look for page number at the end
        match = re.search(r'\.{2,}(\d+)$|(\d+)$', text)
        if match:
            return int(match.group(1) or match.group(2))
        return None
    
    def _find_node_by_title(self, nodes: List[DocumentNode], title: str) -> Optional[DocumentNode]:
        """Find node by title (fuzzy match)"""
        title_lower = title.lower().strip()
        for node in nodes:
            if title_lower in node.title.lower():
                return node
            if node.children:
                found = self._find_node_by_title(node.children, title)
                if found:
                    return found
        return None
    
    def _flatten_hierarchy(self, nodes: List[DocumentNode]) -> List[DocumentNode]:
        """Flatten hierarchy into a list"""
        flat = []
        for node in nodes:
            flat.append(node)
            if node.children:
                flat.extend(self._flatten_hierarchy(node.children))
        return flat
    
    def _find_section_for_page(self, nodes: List[DocumentNode], page_num: int) -> Optional[DocumentNode]:
        """Find the section that contains a given page"""
        for i, node in enumerate(nodes):
            next_start = nodes[i + 1].page_start if i + 1 < len(nodes) else float('inf')
            if node.page_start and node.page_start <= page_num < next_start:
                return node
        return nodes[-1] if nodes else None
    
    def generate_folder_structure(self, root: DocumentNode, base_path: Path) -> Dict[str, Path]:
        """Generate folder structure based on document hierarchy"""
        paths = {}
        
        def create_folders(node: DocumentNode, parent_path: Path, depth: int = 0):
            # Create folder for this node
            if node.level > 0:  # Skip root
                folder_name = f"{depth:02d}_{node.slug}"
                node_path = parent_path / folder_name
                node_path.mkdir(parents=True, exist_ok=True)
                paths[id(node)] = node_path
            else:
                node_path = parent_path
                paths[id(node)] = node_path
                
            # Create subfolders for children
            for i, child in enumerate(node.children):
                create_folders(child, node_path, i + 1)
                
        create_folders(root, base_path)
        return paths