import logging
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
import pdfplumber
from dataclasses import dataclass
import re
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Represents a block of text with metadata"""
    content: str
    page_num: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    block_type: str = "paragraph"  # heading1, heading2, heading3, paragraph, list, etc.
    confidence: float = 1.0


class TextExtractor:
    """Advanced text extraction from PDF files"""
    
    def __init__(self, use_ocr: bool = True, ocr_threshold: float = 0.5):
        self.use_ocr = use_ocr
        self.ocr_threshold = ocr_threshold
        self.heading_patterns = {
            'chapter': re.compile(r'^(Chapter|CHAPTER|Section|SECTION)\s+\d+', re.IGNORECASE),
            'numbered': re.compile(r'^\d+\.?\d*\.?\s+\w+'),
            'lettered': re.compile(r'^[A-Z]\.\s+\w+'),
        }
        
    def extract(self, pdf_path: Path) -> List[TextBlock]:
        """Extract text blocks from PDF with structure analysis"""
        text_blocks = []
        
        # Try PyMuPDF first for better structure preservation
        try:
            text_blocks.extend(self._extract_with_pymupdf(pdf_path))
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}, falling back to pdfplumber")
            
        # Fallback or supplement with pdfplumber
        if not text_blocks:
            try:
                text_blocks.extend(self._extract_with_pdfplumber(pdf_path))
            except Exception as e:
                logger.error(f"PDFPlumber extraction failed: {e}")
                
        # OCR for scanned pages if enabled
        if self.use_ocr and self._needs_ocr(text_blocks):
            text_blocks.extend(self._extract_with_ocr(pdf_path))
            
        # Analyze and classify text blocks
        text_blocks = self._analyze_text_structure(text_blocks)
        
        return text_blocks
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> List[TextBlock]:
        """Extract text using PyMuPDF with formatting info"""
        blocks = []
        
        with fitz.open(str(pdf_path)) as doc:
            for page_num, page in enumerate(doc, 1):
                # Get text blocks with detailed info
                page_dict = page.get_text("dict")
                
                for block in page_dict["blocks"]:
                    if block["type"] == 0:  # Text block
                        text_content = ""
                        avg_font_size = 0
                        font_counts = {}
                        
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text_content += span["text"]
                                avg_font_size += span["size"]
                                font_name = span.get("font", "")
                                font_counts[font_name] = font_counts.get(font_name, 0) + 1
                                
                        if text_content.strip():
                            # Calculate average font size
                            span_count = sum(len(line.get("spans", [])) for line in block.get("lines", []))
                            if span_count > 0:
                                avg_font_size /= span_count
                                
                            # Get most common font
                            most_common_font = max(font_counts.items(), key=lambda x: x[1])[0] if font_counts else None
                            
                            blocks.append(TextBlock(
                                content=text_content.strip(),
                                page_num=page_num,
                                bbox=block["bbox"],
                                font_size=avg_font_size,
                                font_name=most_common_font
                            ))
                            
        return blocks
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> List[TextBlock]:
        """Extract text using pdfplumber as fallback"""
        blocks = []
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text with layout preservation
                text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
                
                if text:
                    # Split into paragraphs
                    paragraphs = re.split(r'\n\s*\n', text)
                    
                    for para in paragraphs:
                        if para.strip():
                            blocks.append(TextBlock(
                                content=para.strip(),
                                page_num=page_num,
                                bbox=(0, 0, page.width, page.height),  # Full page bbox as fallback
                            ))
                            
        return blocks
    
    def _extract_with_ocr(self, pdf_path: Path) -> List[TextBlock]:
        """Extract text using OCR for scanned pages"""
        blocks = []
        
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            # Convert PDF pages to images
            images = convert_from_path(str(pdf_path), dpi=300)
            
            for page_num, image in enumerate(images, 1):
                # Perform OCR
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                # Group text by blocks
                current_block = ""
                block_confidence = []
                
                for i, text in enumerate(ocr_data['text']):
                    if text.strip():
                        current_block += text + " "
                        block_confidence.append(ocr_data['conf'][i])
                    elif current_block:
                        # End of block
                        avg_confidence = sum(block_confidence) / len(block_confidence) if block_confidence else 0
                        
                        if avg_confidence > self.ocr_threshold * 100:
                            blocks.append(TextBlock(
                                content=current_block.strip(),
                                page_num=page_num,
                                bbox=(0, 0, image.width, image.height),
                                confidence=avg_confidence / 100
                            ))
                        
                        current_block = ""
                        block_confidence = []
                        
        except ImportError:
            logger.warning("OCR libraries not available. Install pytesseract and pdf2image for OCR support.")
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            
        return blocks
    
    def _needs_ocr(self, blocks: List[TextBlock]) -> bool:
        """Determine if OCR is needed based on extracted text"""
        if not blocks:
            return True
            
        # Check if text content is too sparse
        total_text = sum(len(block.content) for block in blocks)
        avg_text_per_page = total_text / max(block.page_num for block in blocks) if blocks else 0
        
        return avg_text_per_page < 100  # Threshold for sparse text
    
    def _analyze_text_structure(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """Analyze and classify text blocks by type"""
        if not blocks:
            return blocks
            
        # Calculate font size statistics
        font_sizes = [b.font_size for b in blocks if b.font_size]
        if font_sizes:
            avg_font_size = sum(font_sizes) / len(font_sizes)
            max_font_size = max(font_sizes)
            
            for block in blocks:
                # Classify based on font size and patterns
                if block.font_size:
                    if block.font_size > avg_font_size * 1.5:
                        block.block_type = "heading1"
                    elif block.font_size > avg_font_size * 1.2:
                        block.block_type = "heading2"
                    elif block.font_size > avg_font_size * 1.1:
                        block.block_type = "heading3"
                        
                # Check for heading patterns
                content = block.content.strip()
                if any(pattern.match(content) for pattern in self.heading_patterns.values()):
                    if block.block_type == "paragraph":
                        block.block_type = "heading2"
                        
                # Check for list items
                if re.match(r'^[\-\*\•]\s+', content) or re.match(r'^\d+\.\s+', content):
                    block.block_type = "list"
                    
        return blocks
    
    def get_document_outline(self, blocks: List[TextBlock]) -> Dict[str, Any]:
        """Generate document outline from text blocks"""
        outline = {
            "title": None,
            "sections": [],
            "total_pages": max(b.page_num for b in blocks) if blocks else 0
        }
        
        current_section = None
        current_subsection = None
        
        for block in blocks:
            if block.block_type == "heading1":
                if not outline["title"]:
                    outline["title"] = block.content
                else:
                    current_section = {
                        "title": block.content,
                        "page": block.page_num,
                        "subsections": [],
                        "content": []
                    }
                    outline["sections"].append(current_section)
                    current_subsection = None
                    
            elif block.block_type == "heading2" and current_section:
                current_subsection = {
                    "title": block.content,
                    "page": block.page_num,
                    "content": []
                }
                current_section["subsections"].append(current_subsection)
                
            elif block.block_type in ["paragraph", "list"]:
                if current_subsection:
                    current_subsection["content"].append(block)
                elif current_section:
                    current_section["content"].append(block)
                    
        return outline