from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import json


@dataclass
class ConversionConfig:
    """Configuration for PDF to Markdown conversion"""
    
    # Extraction settings
    extract_images: bool = True
    extract_tables: bool = True
    extract_code: bool = True
    use_ocr: bool = True
    ocr_language: str = 'eng'
    ocr_confidence_threshold: float = 0.5
    
    # Image extraction settings
    min_image_width: int = 50
    min_image_height: int = 50
    extract_inline_images: bool = False
    detect_duplicate_images: bool = True
    image_output_format: str = 'png'  # png, jpg, webp
    image_quality: int = 95
    
    # Table extraction settings
    table_extraction_method: str = 'auto'  # auto, pdfplumber, tabula, camelot
    min_table_rows: int = 2
    min_table_cols: int = 2
    export_table_formats: List[str] = field(default_factory=lambda: ['markdown', 'csv'])
    
    # Code extraction settings
    detect_code_blocks: bool = True
    min_code_lines: int = 2
    highlight_code: bool = True
    export_code_files: bool = True
    
    # Structure analysis settings
    detect_toc: bool = True
    max_hierarchy_depth: int = 4
    merge_single_child_sections: bool = True
    remove_empty_sections: bool = True
    
    # Markdown generation settings
    heading_style: str = 'atx'  # atx (#), setext (underline)
    code_fence_style: str = 'backticks'  # backticks, tildes
    table_alignment: str = 'left'  # left, center, right
    max_line_length: Optional[int] = 100
    image_link_style: str = 'relative'  # relative, absolute, embedded
    use_html_images: bool = False  # Use HTML tags for better image formatting
    
    # Output settings
    create_folder_structure: bool = True
    folder_naming_pattern: str = '{number:02d}_{slug}'
    file_naming_pattern: str = 'index.md'
    generate_toc: bool = True
    generate_index: bool = True
    
    # Processing settings
    parallel_processing: bool = True
    num_workers: Optional[int] = None  # None = auto-detect
    batch_size: int = 10
    verbose: bool = False
    debug: bool = False
    
    # Custom patterns
    custom_heading_patterns: List[str] = field(default_factory=list)
    custom_code_patterns: Dict[str, List[str]] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'ConversionConfig':
        """Load configuration from YAML file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_path: Path) -> 'ConversionConfig':
        """Load configuration from JSON file"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_yaml(self, yaml_path: Path):
        """Save configuration to YAML file"""
        data = self.__dict__.copy()
        # Convert Path objects to strings
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def to_json(self, json_path: Path):
        """Save configuration to JSON file"""
        data = self.__dict__.copy()
        # Convert Path objects to strings
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def validate(self) -> List[str]:
        """Validate configuration settings"""
        errors = []
        
        # Validate numeric ranges
        if self.min_image_width < 1:
            errors.append("min_image_width must be at least 1")
        if self.min_image_height < 1:
            errors.append("min_image_height must be at least 1")
        if self.image_quality < 1 or self.image_quality > 100:
            errors.append("image_quality must be between 1 and 100")
        if self.ocr_confidence_threshold < 0 or self.ocr_confidence_threshold > 1:
            errors.append("ocr_confidence_threshold must be between 0 and 1")
        if self.max_hierarchy_depth < 1:
            errors.append("max_hierarchy_depth must be at least 1")
        
        # Validate string options
        valid_heading_styles = ['atx', 'setext']
        if self.heading_style not in valid_heading_styles:
            errors.append(f"heading_style must be one of {valid_heading_styles}")
        
        valid_table_methods = ['auto', 'pdfplumber', 'tabula', 'camelot']
        if self.table_extraction_method not in valid_table_methods:
            errors.append(f"table_extraction_method must be one of {valid_table_methods}")
        
        valid_image_formats = ['png', 'jpg', 'jpeg', 'webp']
        if self.image_output_format not in valid_image_formats:
            errors.append(f"image_output_format must be one of {valid_image_formats}")
        
        return errors


def get_default_config() -> ConversionConfig:
    """Get default configuration"""
    return ConversionConfig()


def create_example_config_file(output_path: Path):
    """Create an example configuration file"""
    config = ConversionConfig(
        extract_images=True,
        extract_tables=True,
        extract_code=True,
        use_ocr=True,
        ocr_language='eng',
        min_image_width=100,
        min_image_height=100,
        table_extraction_method='auto',
        export_table_formats=['markdown', 'csv', 'json'],
        create_folder_structure=True,
        generate_toc=True,
        verbose=True
    )
    
    if output_path.suffix == '.yaml' or output_path.suffix == '.yml':
        config.to_yaml(output_path)
    elif output_path.suffix == '.json':
        config.to_json(output_path)
    else:
        # Default to YAML
        output_path = output_path.with_suffix('.yaml')
        config.to_yaml(output_path)
    
    return output_path