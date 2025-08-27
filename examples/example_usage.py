"""
Example usage of PDF to Markdown converter
"""

from pathlib import Path
from pdf_to_markdown import PDFToMarkdownConverter, ConversionConfig


def basic_conversion():
    """Basic PDF to Markdown conversion"""
    
    # Create converter with default settings
    converter = PDFToMarkdownConverter()
    
    # Convert PDF
    result = converter.convert(
        pdf_path=Path("sample.pdf"),
        output_dir=Path("output")
    )
    
    print(f"Conversion complete! Main file: {result}")


def custom_configuration():
    """Conversion with custom configuration"""
    
    # Create custom configuration
    config = ConversionConfig(
        # Extraction settings
        extract_images=True,
        extract_tables=True,
        extract_code=True,
        use_ocr=True,
        
        # Image settings
        min_image_width=100,
        min_image_height=100,
        image_output_format='png',
        
        # Table settings
        table_extraction_method='auto',
        export_table_formats=['markdown', 'csv', 'json'],
        
        # Structure settings
        create_folder_structure=True,
        max_hierarchy_depth=3,
        
        # Output settings
        generate_toc=True,
        verbose=True
    )
    
    # Create converter
    converter = PDFToMarkdownConverter(config)
    
    # Convert
    result = converter.convert(
        pdf_path=Path("document.pdf"),
        output_dir=Path("structured_output")
    )
    
    return result


def batch_conversion():
    """Convert multiple PDFs in batch"""
    
    # Configuration for batch processing
    config = ConversionConfig(
        parallel_processing=True,
        num_workers=4,
        verbose=True
    )
    
    # Create converter
    converter = PDFToMarkdownConverter(config)
    
    # List of PDFs to convert
    pdf_files = [
        Path("doc1.pdf"),
        Path("doc2.pdf"),
        Path("doc3.pdf")
    ]
    
    # Batch convert
    results = converter.batch_convert(
        pdf_files=pdf_files,
        output_base_dir=Path("batch_output")
    )
    
    # Process results
    for pdf_path, output_path, error in results:
        if output_path:
            print(f"✓ {pdf_path.name} -> {output_path}")
        else:
            print(f"✗ {pdf_path.name}: {error}")


def selective_extraction():
    """Extract only specific content types"""
    
    # Extract only images and tables, skip code
    config = ConversionConfig(
        extract_images=True,
        extract_tables=True,
        extract_code=False,  # Skip code extraction
        use_ocr=False,        # Skip OCR
        create_folder_structure=False  # Flat structure
    )
    
    converter = PDFToMarkdownConverter(config)
    
    result = converter.convert(
        pdf_path=Path("report.pdf"),
        output_dir=Path("report_output")
    )
    
    return result


def ocr_for_scanned_pdfs():
    """Handle scanned PDFs with OCR"""
    
    config = ConversionConfig(
        use_ocr=True,
        ocr_language='eng',  # English OCR
        ocr_confidence_threshold=0.6,
        extract_images=True,
        verbose=True
    )
    
    converter = PDFToMarkdownConverter(config)
    
    result = converter.convert(
        pdf_path=Path("scanned_document.pdf"),
        output_dir=Path("ocr_output")
    )
    
    return result


def load_config_from_file():
    """Load configuration from YAML file"""
    
    # Load config from YAML
    config = ConversionConfig.from_yaml(Path("config.yaml"))
    
    # Or from JSON
    # config = ConversionConfig.from_json(Path("config.json"))
    
    converter = PDFToMarkdownConverter(config)
    
    result = converter.convert(
        pdf_path=Path("manual.pdf"),
        output_dir=Path("manual_output")
    )
    
    return result


def analyze_pdf_structure():
    """Analyze PDF structure without full conversion"""
    
    from pdf_to_markdown.extractors import TextExtractor
    from pdf_to_markdown.structure_analyzer import DocumentStructureAnalyzer
    
    # Extract text blocks
    text_extractor = TextExtractor(use_ocr=False)
    text_blocks = text_extractor.extract(Path("document.pdf"))
    
    # Analyze structure
    analyzer = DocumentStructureAnalyzer()
    structure = analyzer.analyze(text_blocks)
    
    # Get outline
    outline = text_extractor.get_document_outline(text_blocks)
    
    print("Document Structure:")
    print(f"Title: {outline['title']}")
    print(f"Total pages: {outline['total_pages']}")
    print(f"Sections: {len(outline['sections'])}")
    
    return structure


def custom_markdown_formatting():
    """Customize Markdown output formatting"""
    
    config = ConversionConfig(
        # Markdown formatting options
        heading_style='atx',  # Use # for headings
        code_fence_style='backticks',  # Use ``` for code blocks
        table_alignment='center',  # Center-align tables
        max_line_length=80,  # Wrap lines at 80 characters
        image_link_style='relative',  # Use relative paths for images
        
        # Other settings
        create_folder_structure=True,
        generate_toc=True,
        verbose=True
    )
    
    converter = PDFToMarkdownConverter(config)
    
    result = converter.convert(
        pdf_path=Path("technical_doc.pdf"),
        output_dir=Path("formatted_output")
    )
    
    return result


def extract_specific_pages():
    """Extract content from specific pages only"""
    
    from pdf_to_markdown.extractors import TextExtractor, ImageExtractor
    
    # Note: This requires custom implementation
    # Example of how you might extend the extractor
    
    class CustomTextExtractor(TextExtractor):
        def __init__(self, pages_to_extract=None, **kwargs):
            super().__init__(**kwargs)
            self.pages_to_extract = pages_to_extract or []
        
        def extract(self, pdf_path):
            all_blocks = super().extract(pdf_path)
            
            if self.pages_to_extract:
                # Filter blocks by page number
                filtered = [
                    block for block in all_blocks 
                    if block.page_num in self.pages_to_extract
                ]
                return filtered
            
            return all_blocks
    
    # Use custom extractor
    config = ConversionConfig()
    converter = PDFToMarkdownConverter(config)
    
    # Replace the default extractor
    converter.text_extractor = CustomTextExtractor(
        pages_to_extract=[1, 2, 5, 10],  # Extract only these pages
        use_ocr=False
    )
    
    result = converter.convert(
        pdf_path=Path("large_document.pdf"),
        output_dir=Path("selected_pages_output")
    )
    
    return result


def main():
    """Run examples"""
    
    print("PDF to Markdown Converter - Examples")
    print("=" * 40)
    
    # Choose which example to run
    examples = {
        1: ("Basic Conversion", basic_conversion),
        2: ("Custom Configuration", custom_configuration),
        3: ("Batch Conversion", batch_conversion),
        4: ("Selective Extraction", selective_extraction),
        5: ("OCR for Scanned PDFs", ocr_for_scanned_pdfs),
        6: ("Load Config from File", load_config_from_file),
        7: ("Analyze PDF Structure", analyze_pdf_structure),
        8: ("Custom Markdown Formatting", custom_markdown_formatting),
    }
    
    print("\nAvailable examples:")
    for num, (name, _) in examples.items():
        print(f"{num}. {name}")
    
    # Note: In actual use, you would uncomment one of these
    # basic_conversion()
    # custom_configuration()
    # batch_conversion()
    
    print("\nUncomment the desired example in the code to run it.")


if __name__ == "__main__":
    main()