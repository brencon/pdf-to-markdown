import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import shutil
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import ConversionConfig
from .extractors import TextExtractor, ImageExtractor, TableExtractor, CodeBlockExtractor
from .structure_analyzer import DocumentStructureAnalyzer
from .markdown_generator import MarkdownGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PDFToMarkdownConverter:
    """Main converter class for PDF to Markdown transformation"""
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        self.config = config or ConversionConfig()
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
        
        # Initialize extractors
        self.text_extractor = TextExtractor(
            use_ocr=self.config.use_ocr,
            ocr_threshold=self.config.ocr_confidence_threshold
        )
        
        self.image_extractor = ImageExtractor(
            min_width=self.config.min_image_width,
            min_height=self.config.min_image_height,
            extract_inline=self.config.extract_inline_images,
            detect_duplicates=self.config.detect_duplicate_images
        ) if self.config.extract_images else None
        
        self.table_extractor = TableExtractor(
            method=self.config.table_extraction_method,
            min_rows=self.config.min_table_rows,
            min_cols=self.config.min_table_cols
        ) if self.config.extract_tables else None
        
        self.code_extractor = CodeBlockExtractor() if self.config.extract_code else None
        
        # Initialize analyzers and generators
        self.structure_analyzer = DocumentStructureAnalyzer()
        self.markdown_generator = MarkdownGenerator({
            'heading_style': self.config.heading_style,
            'code_fence_style': self.config.code_fence_style,
            'table_alignment': self.config.table_alignment,
            'max_line_length': self.config.max_line_length,
            'image_format': self.config.image_link_style
        })
        
        # Set logging level
        if self.config.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        elif self.config.verbose:
            logging.getLogger().setLevel(logging.INFO)
        else:
            logging.getLogger().setLevel(logging.WARNING)
    
    def convert(self, pdf_path: Path, output_dir: Path) -> Path:
        """Convert PDF to Markdown with folder structure"""
        
        # Validate input
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting conversion of {pdf_path}")
        
        # Step 1: Extract content
        logger.info("Step 1: Extracting content from PDF...")
        extracted_content = self._extract_content(pdf_path)
        
        # Step 2: Analyze document structure
        logger.info("Step 2: Analyzing document structure...")
        document_structure = self._analyze_structure(extracted_content)
        
        # Step 3: Create folder structure
        logger.info("Step 3: Creating folder structure...")
        folder_paths = self._create_folder_structure(document_structure, output_dir)
        
        # Step 4: Export assets (images, tables, code)
        logger.info("Step 4: Exporting assets...")
        asset_paths = self._export_assets(extracted_content, output_dir)
        
        # Step 5: Generate Markdown files
        logger.info("Step 5: Generating Markdown files...")
        index_path = self._generate_markdown(
            document_structure, 
            output_dir,
            asset_paths
        )
        
        # Step 6: Create metadata file
        logger.info("Step 6: Creating metadata...")
        self._create_metadata(pdf_path, output_dir, extracted_content, document_structure)
        
        logger.info(f"Conversion complete! Output saved to {output_dir}")
        
        return index_path
    
    def _extract_content(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract all content from PDF"""
        content = {}
        
        # Extract text
        with tqdm(desc="Extracting text", unit="blocks") as pbar:
            text_blocks = self.text_extractor.extract(pdf_path)
            content['text_blocks'] = text_blocks
            pbar.update(len(text_blocks))
            logger.info(f"Extracted {len(text_blocks)} text blocks")
        
        # Extract images if enabled
        if self.config.extract_images and self.image_extractor:
            with tqdm(desc="Extracting images", unit="images") as pbar:
                images = self.image_extractor.extract(pdf_path)
                content['images'] = images
                pbar.update(len(images))
                logger.info(f"Extracted {len(images)} images")
        else:
            content['images'] = []
        
        # Extract tables if enabled
        if self.config.extract_tables and self.table_extractor:
            with tqdm(desc="Extracting tables", unit="tables") as pbar:
                tables = self.table_extractor.extract(pdf_path)
                content['tables'] = tables
                pbar.update(len(tables))
                logger.info(f"Extracted {len(tables)} tables")
        else:
            content['tables'] = []
        
        # Extract code blocks if enabled
        if self.config.extract_code and self.code_extractor:
            with tqdm(desc="Extracting code blocks", unit="blocks") as pbar:
                code_blocks = self.code_extractor.extract(text_blocks)
                content['code_blocks'] = code_blocks
                pbar.update(len(code_blocks))
                logger.info(f"Extracted {len(code_blocks)} code blocks")
        else:
            content['code_blocks'] = []
        
        return content
    
    def _analyze_structure(self, content: Dict[str, Any]) -> Any:
        """Analyze document structure"""
        return self.structure_analyzer.analyze(
            content['text_blocks'],
            content.get('images', []),
            content.get('tables', []),
            content.get('code_blocks', [])
        )
    
    def _create_folder_structure(self, document_structure: Any, output_dir: Path) -> Dict[Any, Path]:
        """Create folder structure based on document hierarchy"""
        if not self.config.create_folder_structure:
            return {document_structure: output_dir}
        
        return self.structure_analyzer.generate_folder_structure(document_structure, output_dir)
    
    def _export_assets(self, content: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Export images, tables, and code blocks"""
        asset_paths = {}
        
        # Export images
        if content.get('images') and self.image_extractor:
            images_dir = output_dir / 'assets' / 'images'
            with tqdm(desc="Exporting images", total=len(content['images'])) as pbar:
                image_paths = self.image_extractor.save_images(content['images'], images_dir)
                asset_paths['images'] = image_paths
                pbar.update(len(image_paths))
                logger.info(f"Exported {len(image_paths)} images")
        
        # Export tables
        if content.get('tables') and self.table_extractor:
            tables_dir = output_dir / 'assets' / 'tables'
            with tqdm(desc="Exporting tables", total=len(content['tables'])) as pbar:
                table_paths = self.table_extractor.export_tables(
                    content['tables'], 
                    tables_dir,
                    self.config.export_table_formats
                )
                asset_paths['tables'] = table_paths
                pbar.update(len(table_paths))
                logger.info(f"Exported {len(table_paths)} tables")
        
        # Export code blocks
        if content.get('code_blocks') and self.code_extractor and self.config.export_code_files:
            code_dir = output_dir / 'assets' / 'code'
            with tqdm(desc="Exporting code blocks", total=len(content['code_blocks'])) as pbar:
                code_paths = self.code_extractor.export_code_blocks(content['code_blocks'], code_dir)
                asset_paths['code'] = code_paths
                pbar.update(len(code_paths))
                logger.info(f"Exported {len(code_paths)} code blocks")
        
        return asset_paths
    
    def _generate_markdown(self, document_structure: Any, output_dir: Path, 
                          asset_paths: Dict[str, Any]) -> Path:
        """Generate Markdown files"""
        return self.markdown_generator.generate_document(
            document_structure,
            output_dir,
            asset_paths.get('images'),
            asset_paths.get('tables'),
            asset_paths.get('code')
        )
    
    def _create_metadata(self, pdf_path: Path, output_dir: Path, 
                        content: Dict[str, Any], document_structure: Any):
        """Create metadata file with conversion information"""
        import json
        from datetime import datetime
        
        metadata = {
            'source_pdf': str(pdf_path.name),
            'conversion_date': datetime.now().isoformat(),
            'converter_version': '1.0.0',
            'configuration': {
                'extract_images': self.config.extract_images,
                'extract_tables': self.config.extract_tables,
                'extract_code': self.config.extract_code,
                'use_ocr': self.config.use_ocr,
            },
            'statistics': {
                'text_blocks': len(content.get('text_blocks', [])),
                'images': len(content.get('images', [])),
                'tables': len(content.get('tables', [])),
                'code_blocks': len(content.get('code_blocks', [])),
                'sections': self._count_sections(document_structure)
            }
        }
        
        metadata_file = output_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Created metadata file: {metadata_file}")
    
    def _count_sections(self, node: Any) -> int:
        """Count total number of sections in document structure"""
        count = 0
        if hasattr(node, 'node_type') and node.node_type != 'root':
            count = 1
        for child in getattr(node, 'children', []):
            count += self._count_sections(child)
        return count
    
    def batch_convert(self, pdf_files: List[Path], output_base_dir: Path):
        """Convert multiple PDF files in batch"""
        results = []
        
        if self.config.parallel_processing:
            # Parallel processing
            num_workers = self.config.num_workers or 4
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = {}
                for pdf_path in pdf_files:
                    output_dir = output_base_dir / pdf_path.stem
                    future = executor.submit(self.convert, pdf_path, output_dir)
                    futures[future] = pdf_path
                
                for future in tqdm(as_completed(futures), total=len(futures), desc="Converting PDFs"):
                    pdf_path = futures[future]
                    try:
                        result = future.result()
                        results.append((pdf_path, result, None))
                    except Exception as e:
                        logger.error(f"Failed to convert {pdf_path}: {e}")
                        results.append((pdf_path, None, str(e)))
        else:
            # Sequential processing
            for pdf_path in tqdm(pdf_files, desc="Converting PDFs"):
                output_dir = output_base_dir / pdf_path.stem
                try:
                    result = self.convert(pdf_path, output_dir)
                    results.append((pdf_path, result, None))
                except Exception as e:
                    logger.error(f"Failed to convert {pdf_path}: {e}")
                    results.append((pdf_path, None, str(e)))
        
        # Summary
        successful = sum(1 for _, result, _ in results if result)
        logger.info(f"Batch conversion complete: {successful}/{len(pdf_files)} successful")
        
        return results