"""
Content merger for combining text and images in reading order
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass 
class ContentBlock:
    """Unified content block that can be text or image"""
    content_type: str  # 'text', 'image', 'table', 'code'
    content: Any  # The actual content object
    page_num: int
    y_position: float  # Top y-coordinate for ordering
    height: float  # Height of the block
    
    @property
    def y_end(self) -> float:
        """Bottom y-coordinate"""
        return self.y_position + self.height


class ContentMerger:
    """Merges different content types in reading order"""
    
    def __init__(self):
        self.overlap_threshold = 0.5  # How much overlap before considering side-by-side
        
    def merge_content(self, text_blocks: List[Any], images: List[Any] = None, 
                     tables: List[Any] = None) -> List[ContentBlock]:
        """Merge all content types in reading order"""
        merged_content = []
        
        # Convert text blocks to ContentBlocks
        for text_block in text_blocks:
            if hasattr(text_block, 'bbox'):
                y_pos = text_block.bbox[1] if len(text_block.bbox) > 1 else 0
                height = text_block.bbox[3] - text_block.bbox[1] if len(text_block.bbox) > 3 else 20
            else:
                y_pos = 0
                height = 20
                
            merged_content.append(ContentBlock(
                content_type='text',
                content=text_block,
                page_num=getattr(text_block, 'page_num', 1),
                y_position=y_pos,
                height=height
            ))
        
        # Convert images to ContentBlocks
        if images:
            for img in images:
                if hasattr(img, 'bbox'):
                    y_pos = img.bbox[1] if len(img.bbox) > 1 else 0
                    height = img.bbox[3] - img.bbox[1] if len(img.bbox) > 3 else 100
                else:
                    y_pos = 0
                    height = 100
                    
                merged_content.append(ContentBlock(
                    content_type='image',
                    content=img,
                    page_num=getattr(img, 'page_num', 1),
                    y_position=y_pos,
                    height=height
                ))
        
        # Convert tables to ContentBlocks
        if tables:
            for table in tables:
                if hasattr(table, 'bbox'):
                    y_pos = table.bbox[1] if len(table.bbox) > 1 else 0
                    height = table.bbox[3] - table.bbox[1] if len(table.bbox) > 3 else 50
                else:
                    y_pos = 0
                    height = 50
                    
                merged_content.append(ContentBlock(
                    content_type='table',
                    content=table,
                    page_num=getattr(table, 'page_num', 1),
                    y_position=y_pos,
                    height=height
                ))
        
        # Sort by page, then by y-position (reading order)
        merged_content.sort(key=lambda x: (x.page_num, x.y_position))
        
        # Handle side-by-side content (images next to text)
        merged_content = self._handle_side_by_side(merged_content)
        
        return merged_content
    
    def _handle_side_by_side(self, content_blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Handle content that appears side-by-side (like wrapped text around images)"""
        if len(content_blocks) < 2:
            return content_blocks
            
        result = []
        i = 0
        
        while i < len(content_blocks):
            current = content_blocks[i]
            
            # Check if next item is side-by-side
            if i + 1 < len(content_blocks):
                next_block = content_blocks[i + 1]
                
                # Check for significant vertical overlap (side-by-side)
                if self._blocks_overlap(current, next_block):
                    # For side-by-side content, put image first if it's smaller
                    if current.content_type == 'image' and next_block.content_type == 'text':
                        result.append(current)
                        result.append(next_block)
                        i += 2
                    elif current.content_type == 'text' and next_block.content_type == 'image':
                        # Check if image is small (likely inline/wrapped)
                        if next_block.height < current.height * 1.5:
                            result.append(next_block)  # Image first for wrapping
                            result.append(current)
                            i += 2
                        else:
                            result.append(current)
                            i += 1
                    else:
                        result.append(current)
                        i += 1
                else:
                    result.append(current)
                    i += 1
            else:
                result.append(current)
                i += 1
                
        return result
    
    def _blocks_overlap(self, block1: ContentBlock, block2: ContentBlock) -> bool:
        """Check if two blocks overlap vertically"""
        if block1.page_num != block2.page_num:
            return False
            
        # Calculate overlap
        overlap_start = max(block1.y_position, block2.y_position)
        overlap_end = min(block1.y_end, block2.y_end)
        
        if overlap_end <= overlap_start:
            return False
            
        overlap_height = overlap_end - overlap_start
        min_height = min(block1.height, block2.height)
        
        # Consider overlapping if overlap is more than threshold of smaller block
        return overlap_height > (min_height * self.overlap_threshold)