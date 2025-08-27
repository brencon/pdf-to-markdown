import logging
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image
import io
from pathlib import Path
import hashlib
from dataclasses import dataclass
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """Represents an extracted image with metadata"""
    image_data: bytes
    page_num: int
    bbox: Tuple[float, float, float, float]
    width: int
    height: int
    format: str
    hash: str
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    image_type: str = "figure"  # figure, diagram, chart, photo, logo, etc.


class ImageExtractor:
    """Advanced image extraction from PDF files"""
    
    def __init__(self, min_width: int = 50, min_height: int = 50, 
                 extract_inline: bool = True, detect_duplicates: bool = True):
        self.min_width = min_width
        self.min_height = min_height
        self.extract_inline = extract_inline
        self.detect_duplicates = detect_duplicates
        self.extracted_hashes = set()
        
    def extract(self, pdf_path: Path) -> List[ExtractedImage]:
        """Extract all images from PDF"""
        images = []
        
        with fitz.open(str(pdf_path)) as doc:
            for page_num, page in enumerate(doc, 1):
                # Extract embedded images
                images.extend(self._extract_page_images(page, page_num))
                
                # Extract inline images if enabled
                if self.extract_inline:
                    images.extend(self._extract_inline_images(page, page_num))
                    
        # Remove duplicates if enabled
        if self.detect_duplicates:
            images = self._remove_duplicates(images)
            
        # Classify image types
        images = self._classify_images(images)
        
        return images
    
    def _extract_page_images(self, page, page_num: int) -> List[ExtractedImage]:
        """Extract embedded images from a page"""
        images = []
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            try:
                # Get image reference
                xref = img[0]
                
                # Extract image data
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Get image properties
                width = base_image["width"]
                height = base_image["height"]
                ext = base_image["ext"]
                
                # Skip small images
                if width < self.min_width or height < self.min_height:
                    continue
                    
                # Get image position on page
                bbox = self._get_image_bbox(page, xref)
                
                # Calculate hash for duplicate detection
                image_hash = hashlib.md5(image_bytes).hexdigest()
                
                images.append(ExtractedImage(
                    image_data=image_bytes,
                    page_num=page_num,
                    bbox=bbox,
                    width=width,
                    height=height,
                    format=ext,
                    hash=image_hash
                ))
                
            except Exception as e:
                logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                
        return images
    
    def _extract_inline_images(self, page, page_num: int) -> List[ExtractedImage]:
        """Extract inline images (rendered as part of page content)"""
        images = []
        
        try:
            # Get page pixmap at high resolution
            mat = fitz.Matrix(3, 3)  # 3x zoom for better quality
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.pil_tobytes(format="PNG")
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to OpenCV format for processing
            opencv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Detect image regions using edge detection
            image_regions = self._detect_image_regions(opencv_image)
            
            for region in image_regions:
                x, y, w, h = region
                
                # Skip small regions
                if w < self.min_width * 3 or h < self.min_height * 3:
                    continue
                    
                # Extract region
                cropped = img.crop((x, y, x + w, y + h))
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                cropped.save(img_buffer, format='PNG')
                image_bytes = img_buffer.getvalue()
                
                # Calculate hash
                image_hash = hashlib.md5(image_bytes).hexdigest()
                
                # Convert coordinates back to page coordinates
                bbox = (x/3, y/3, (x+w)/3, (y+h)/3)
                
                images.append(ExtractedImage(
                    image_data=image_bytes,
                    page_num=page_num,
                    bbox=bbox,
                    width=w//3,
                    height=h//3,
                    format='png',
                    hash=image_hash
                ))
                
        except Exception as e:
            logger.warning(f"Failed to extract inline images from page {page_num}: {e}")
            
        return images
    
    def _get_image_bbox(self, page, xref: int) -> Tuple[float, float, float, float]:
        """Get bounding box of image on page"""
        try:
            img_list = page.get_image_rects(xref)
            if img_list:
                rect = img_list[0]
                return (rect.x0, rect.y0, rect.x1, rect.y1)
        except:
            pass
            
        # Fallback to page dimensions
        return (0, 0, page.rect.width, page.rect.height)
    
    def _detect_image_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect distinct image regions in page using computer vision"""
        regions = []
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter based on area and aspect ratio
                area = w * h
                if area > 5000:  # Minimum area threshold
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.2 < aspect_ratio < 5:  # Reasonable aspect ratio
                        regions.append((x, y, w, h))
                        
        except Exception as e:
            logger.debug(f"Error detecting image regions: {e}")
            
        return regions
    
    def _remove_duplicates(self, images: List[ExtractedImage]) -> List[ExtractedImage]:
        """Remove duplicate images based on hash"""
        unique_images = []
        seen_hashes = set()
        
        for img in images:
            if img.hash not in seen_hashes:
                unique_images.append(img)
                seen_hashes.add(img.hash)
            else:
                logger.debug(f"Skipping duplicate image with hash {img.hash}")
                
        return unique_images
    
    def _classify_images(self, images: List[ExtractedImage]) -> List[ExtractedImage]:
        """Classify images by type based on characteristics"""
        for img in images:
            # Open image for analysis
            try:
                pil_img = Image.open(io.BytesIO(img.image_data))
                
                # Check aspect ratio
                aspect_ratio = img.width / img.height if img.height > 0 else 1
                
                # Check if mostly text (OCR would be needed for accurate detection)
                if self._is_likely_diagram(pil_img):
                    img.image_type = "diagram"
                elif self._is_likely_chart(pil_img):
                    img.image_type = "chart"
                elif aspect_ratio > 3 or aspect_ratio < 0.33:
                    img.image_type = "banner"
                elif img.width < 200 and img.height < 200:
                    img.image_type = "icon"
                else:
                    img.image_type = "figure"
                    
            except Exception as e:
                logger.debug(f"Error classifying image: {e}")
                
        return images
    
    def _is_likely_diagram(self, image: Image.Image) -> bool:
        """Check if image is likely a diagram (high contrast, geometric shapes)"""
        try:
            # Convert to grayscale
            gray = image.convert('L')
            
            # Calculate histogram
            hist = gray.histogram()
            
            # Check for high contrast (peaks at extremes)
            low_values = sum(hist[:50])
            high_values = sum(hist[-50:])
            total = sum(hist)
            
            if (low_values + high_values) / total > 0.6:
                return True
                
        except:
            pass
            
        return False
    
    def _is_likely_chart(self, image: Image.Image) -> bool:
        """Check if image is likely a chart (data visualization)"""
        try:
            # Simple heuristic: charts often have white/light backgrounds
            # and distinct color regions
            pixels = image.getdata()
            
            if isinstance(pixels[0], int):
                # Grayscale image, less likely to be a chart
                return False
                
            # Count distinct colors (simplified)
            unique_colors = len(set(list(pixels)[:1000]))  # Sample first 1000 pixels
            
            if unique_colors > 10 and unique_colors < 100:
                return True
                
        except:
            pass
            
        return False
    
    def save_images(self, images: List[ExtractedImage], output_dir: Path, 
                    naming_pattern: str = "image_{page:03d}_{index:03d}") -> Dict[ExtractedImage, Path]:
        """Save extracted images to disk"""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths = {}
        
        # Group images by page
        page_counts = {}
        
        for img in images:
            if img.page_num not in page_counts:
                page_counts[img.page_num] = 0
            page_counts[img.page_num] += 1
            
            index = page_counts[img.page_num]
            
            # Generate filename
            filename = naming_pattern.format(page=img.page_num, index=index)
            filename = f"{filename}_{img.image_type}.{img.format}"
            filepath = output_dir / filename
            
            # Save image
            filepath.write_bytes(img.image_data)
            saved_paths[img] = filepath
            
            logger.info(f"Saved image to {filepath}")
            
        return saved_paths