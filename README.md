# PDF to Markdown Enterprise

A comprehensive, enterprise-grade solution for transforming PDF files into well-structured Markdown with intelligent content organization.

## Features

### Core Capabilities
- **Intelligent Text Extraction**: Advanced text extraction with structure preservation
- **Document Hierarchy Detection**: Automatic detection of chapters, sections, and subsections
- **Smart Folder Organization**: Creates logical folder structure based on document outline
- **Multi-Method Extraction**: Uses multiple PDF libraries for maximum compatibility

### Content Extraction
- **Images**: Extracts embedded and inline images with duplicate detection
- **Tables**: Converts tables to Markdown, CSV, JSON, or Excel formats
- **Code Blocks**: Detects and extracts code snippets with language identification
- **OCR Support**: Handles scanned PDFs using Tesseract OCR

### Advanced Features
- **Table of Contents Generation**: Automatically generates navigation structure
- **Metadata Preservation**: Captures document metadata and conversion statistics
- **Batch Processing**: Convert multiple PDFs with parallel processing support
- **Configurable Output**: Extensive customization options via YAML/JSON config

## Installation

### Prerequisites
- Python 3.8 or higher
- Poppler (for pdf2image)
- Tesseract OCR (optional, for scanned PDFs)

### Install from source
```bash
git clone https://github.com/yourusername/pdf-to-markdown
cd pdf-to-markdown
pip install -e .
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Additional Setup

#### For OCR support (optional):
```bash
# Windows
# Download and install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki

# macOS
brew install tesseract

# Linux
sudo apt-get install tesseract-ocr
```

#### For advanced table extraction (optional):
```bash
# Install Java for tabula-py
# Download from https://www.java.com/

# Install additional dependencies
pip install camelot-py[cv]
```

## Quick Start

### Basic Usage

Convert a single PDF:
```bash
pdf2md convert input.pdf output_folder/
```

### With Options

```bash
pdf2md convert input.pdf output_folder/ \
  --images \
  --tables \
  --code \
  --ocr \
  --verbose
```

### Batch Conversion

Convert all PDFs in a directory:
```bash
pdf2md batch input_folder/ output_folder/ --parallel --workers 4
```

### Using Configuration File

Create a configuration file:
```bash
pdf2md init-config my_config.yaml
```

Use the configuration:
```bash
pdf2md convert input.pdf output_folder/ --config my_config.yaml
```

## Configuration

### Example Configuration (YAML)

```yaml
# Extraction settings
extract_images: true
extract_tables: true
extract_code: true
use_ocr: true
ocr_language: 'eng'

# Image settings
min_image_width: 100
min_image_height: 100
image_output_format: 'png'
detect_duplicate_images: true

# Table settings
table_extraction_method: 'auto'  # auto, pdfplumber, tabula, camelot
export_table_formats:
  - markdown
  - csv
  - json

# Structure settings
create_folder_structure: true
max_hierarchy_depth: 4
generate_toc: true

# Markdown settings
heading_style: 'atx'  # atx (#) or setext (underline)
code_fence_style: 'backticks'
max_line_length: 100

# Processing settings
parallel_processing: true
num_workers: 4
verbose: true
```

## Output Structure

The converter creates an organized folder structure:

```
output_folder/
├── README.md                 # Main index with table of contents
├── metadata.json             # Conversion metadata and statistics
├── 01_introduction/
│   └── index.md             # Chapter content
├── 02_chapter1/
│   ├── index.md
│   ├── 01_section1/
│   │   └── index.md
│   └── 02_section2/
│       └── index.md
└── assets/
    ├── images/              # Extracted images
    │   ├── image_001_001.png
    │   └── image_002_001.png
    ├── tables/              # Extracted tables
    │   ├── table_page001_01.csv
    │   └── table_page001_01.md
    └── code/                # Extracted code blocks
        ├── python_snippet_001.py
        └── sql_query_001.sql
```

## CLI Commands

### convert
Convert a single PDF to Markdown:
```bash
pdf2md convert [OPTIONS] PDF_PATH OUTPUT_DIR

Options:
  -c, --config PATH        Configuration file (YAML or JSON)
  --images / --no-images   Extract images from PDF
  --tables / --no-tables   Extract tables from PDF
  --code / --no-code       Extract code blocks from PDF
  --ocr / --no-ocr         Use OCR for scanned pages
  -v, --verbose            Enable verbose output
  --debug                  Enable debug output
```

### batch
Convert multiple PDFs:
```bash
pdf2md batch [OPTIONS] INPUT_DIR OUTPUT_DIR

Options:
  -c, --config PATH              Configuration file
  -p, --pattern TEXT             File pattern to match PDFs (default: *.pdf)
  --parallel / --sequential      Process files in parallel
  -w, --workers INTEGER          Number of parallel workers
  -v, --verbose                  Enable verbose output
```

### analyze
Analyze PDF structure without conversion:
```bash
pdf2md analyze PDF_PATH
```

### init-config
Create an example configuration file:
```bash
pdf2md init-config [OPTIONS] OUTPUT_PATH

Options:
  -f, --format [yaml|json]  Configuration file format
```

## Python API

```python
from pdf_to_markdown import PDFToMarkdownConverter, ConversionConfig

# Create configuration
config = ConversionConfig(
    extract_images=True,
    extract_tables=True,
    extract_code=True,
    create_folder_structure=True,
    verbose=True
)

# Create converter
converter = PDFToMarkdownConverter(config)

# Convert PDF
result_path = converter.convert(
    pdf_path=Path("input.pdf"),
    output_dir=Path("output_folder")
)

print(f"Conversion complete! Output: {result_path}")
```

## Advanced Usage

### Custom Language Patterns

Add custom patterns for code detection:

```python
config = ConversionConfig(
    custom_code_patterns={
        'custom_lang': [
            r'CUSTOM_KEYWORD',
            r'special_function\(',
        ]
    }
)
```

### Selective Extraction

Extract only specific content types:

```python
config = ConversionConfig(
    extract_images=True,
    extract_tables=False,  # Skip tables
    extract_code=False,     # Skip code blocks
)
```

### OCR Configuration

Configure OCR for specific languages:

```python
config = ConversionConfig(
    use_ocr=True,
    ocr_language='fra',  # French
    ocr_confidence_threshold=0.7
)
```

## Supported Formats

### Input
- PDF files (text-based and scanned)

### Output
- Markdown files (.md)
- Images: PNG, JPG, WebP
- Tables: Markdown, CSV, JSON, Excel
- Code: Original language files with syntax highlighting

## Performance Tips

1. **Parallel Processing**: Enable for batch conversions
2. **Disable Unused Features**: Turn off extraction types you don't need
3. **OCR Optimization**: Only enable OCR for scanned documents
4. **Table Method Selection**: Choose specific method instead of 'auto' for faster processing

## Troubleshooting

### Common Issues

**Issue**: OCR not working
```bash
# Solution: Install Tesseract
# Windows: Download from GitHub
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

**Issue**: Tables not extracting properly
```bash
# Solution: Try different extraction methods
pdf2md convert input.pdf output/ --config config.yaml
# In config.yaml, set:
# table_extraction_method: 'camelot'  # or 'tabula'
```

**Issue**: Memory errors with large PDFs
```bash
# Solution: Process in smaller batches
# Reduce parallel workers or disable parallel processing
pdf2md batch input/ output/ --sequential
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

This project uses the following excellent libraries:
- PyMuPDF for PDF processing
- pdfplumber for table extraction
- Tesseract for OCR
- Pygments for code highlighting
- Rich for CLI interface

## Support

For issues, questions, or suggestions, please open an issue on GitHub.