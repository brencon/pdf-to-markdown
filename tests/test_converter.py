import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from pdf_to_markdown import PDFToMarkdownConverter, ConversionConfig
from pdf_to_markdown.extractors import TextExtractor, ImageExtractor, TableExtractor, CodeBlockExtractor
from pdf_to_markdown.extractors.text_extractor import TextBlock
from pdf_to_markdown.extractors.image_extractor import ExtractedImage
from pdf_to_markdown.extractors.table_extractor import ExtractedTable
from pdf_to_markdown.extractors.code_extractor import CodeBlock


class TestPDFToMarkdownConverter:
    """Test suite for PDFToMarkdownConverter"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration"""
        return ConversionConfig(
            extract_images=True,
            extract_tables=True,
            extract_code=True,
            use_ocr=False,
            verbose=False
        )
    
    @pytest.fixture
    def mock_text_blocks(self):
        """Create mock text blocks"""
        return [
            TextBlock(
                content="Chapter 1: Introduction",
                page_num=1,
                bbox=(0, 0, 100, 50),
                font_size=24,
                block_type="heading1"
            ),
            TextBlock(
                content="This is a paragraph of text.",
                page_num=1,
                bbox=(0, 60, 100, 100),
                font_size=12,
                block_type="paragraph"
            ),
            TextBlock(
                content="Section 1.1: Background",
                page_num=2,
                bbox=(0, 0, 100, 30),
                font_size=18,
                block_type="heading2"
            ),
        ]
    
    def test_converter_initialization(self, sample_config):
        """Test converter initialization with config"""
        converter = PDFToMarkdownConverter(sample_config)
        assert converter.config == sample_config
        assert converter.text_extractor is not None
        assert converter.image_extractor is not None
        assert converter.table_extractor is not None
        assert converter.code_extractor is not None
    
    def test_converter_initialization_no_extractors(self):
        """Test converter with disabled extractors"""
        config = ConversionConfig(
            extract_images=False,
            extract_tables=False,
            extract_code=False
        )
        converter = PDFToMarkdownConverter(config)
        assert converter.image_extractor is None
        assert converter.table_extractor is None
        assert converter.code_extractor is None
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Invalid config
        config = ConversionConfig(
            min_image_width=-1,  # Invalid
            image_quality=150    # Invalid
        )
        
        with pytest.raises(ValueError) as exc_info:
            PDFToMarkdownConverter(config)
        assert "Configuration errors" in str(exc_info.value)
    
    @patch('pdf_to_markdown.converter.TextExtractor')
    @patch('pdf_to_markdown.converter.ImageExtractor')
    def test_extract_content(self, mock_image_ext, mock_text_ext, sample_config, temp_dir):
        """Test content extraction"""
        # Setup mocks
        mock_text_ext_instance = MagicMock()
        mock_text_ext_instance.extract.return_value = [
            TextBlock("Test", 1, (0, 0, 10, 10))
        ]
        mock_text_ext.return_value = mock_text_ext_instance
        
        mock_image_ext_instance = MagicMock()
        mock_image_ext_instance.extract.return_value = []
        mock_image_ext.return_value = mock_image_ext_instance
        
        # Create converter and extract
        converter = PDFToMarkdownConverter(sample_config)
        converter.text_extractor = mock_text_ext_instance
        converter.image_extractor = mock_image_ext_instance
        converter.table_extractor = None
        converter.code_extractor = None
        
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        
        content = converter._extract_content(pdf_path)
        
        assert 'text_blocks' in content
        assert len(content['text_blocks']) == 1
        assert 'images' in content
        assert len(content['images']) == 0
    
    def test_count_sections(self, sample_config):
        """Test section counting"""
        converter = PDFToMarkdownConverter(sample_config)
        
        # Create mock document structure
        from pdf_to_markdown.structure_analyzer import DocumentNode
        
        root = DocumentNode("Document", 0, node_type="root")
        chapter1 = DocumentNode("Chapter 1", 1, node_type="chapter")
        section1 = DocumentNode("Section 1.1", 2, node_type="section")
        section2 = DocumentNode("Section 1.2", 2, node_type="section")
        
        chapter1.children = [section1, section2]
        root.children = [chapter1]
        
        count = converter._count_sections(root)
        assert count == 3  # Chapter 1 + 2 sections
    
    @patch('pdf_to_markdown.converter.PDFToMarkdownConverter._extract_content')
    @patch('pdf_to_markdown.converter.PDFToMarkdownConverter._analyze_structure')
    @patch('pdf_to_markdown.converter.PDFToMarkdownConverter._create_folder_structure')
    @patch('pdf_to_markdown.converter.PDFToMarkdownConverter._export_assets')
    @patch('pdf_to_markdown.converter.PDFToMarkdownConverter._generate_markdown')
    @patch('pdf_to_markdown.converter.PDFToMarkdownConverter._create_metadata')
    def test_convert_workflow(self, mock_metadata, mock_gen_md, mock_export, 
                             mock_folders, mock_analyze, mock_extract,
                             sample_config, temp_dir):
        """Test complete conversion workflow"""
        # Setup mocks
        mock_extract.return_value = {'text_blocks': [], 'images': [], 'tables': [], 'code_blocks': []}
        mock_analyze.return_value = Mock()
        mock_folders.return_value = {}
        mock_export.return_value = {}
        mock_gen_md.return_value = temp_dir / "index.md"
        
        # Create converter and test PDF
        converter = PDFToMarkdownConverter(sample_config)
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        output_dir = temp_dir / "output"
        
        # Run conversion
        result = converter.convert(pdf_path, output_dir)
        
        # Verify workflow
        assert result == temp_dir / "index.md"
        mock_extract.assert_called_once()
        mock_analyze.assert_called_once()
        mock_folders.assert_called_once()
        mock_export.assert_called_once()
        mock_gen_md.assert_called_once()
        mock_metadata.assert_called_once()
    
    def test_batch_convert(self, sample_config, temp_dir):
        """Test batch conversion"""
        # Create test PDFs
        pdf1 = temp_dir / "test1.pdf"
        pdf2 = temp_dir / "test2.pdf"
        pdf1.touch()
        pdf2.touch()
        
        # Mock convert method
        converter = PDFToMarkdownConverter(sample_config)
        converter.convert = Mock(return_value=temp_dir / "index.md")
        
        # Run batch conversion
        results = converter.batch_convert([pdf1, pdf2], temp_dir / "output")
        
        assert len(results) == 2
        assert converter.convert.call_count == 2


class TestConversionConfig:
    """Test suite for ConversionConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ConversionConfig()
        assert config.extract_images is True
        assert config.extract_tables is True
        assert config.extract_code is True
        assert config.use_ocr is True
        assert config.min_image_width == 50
        assert config.min_image_height == 50
    
    def test_config_validation_valid(self):
        """Test validation with valid config"""
        config = ConversionConfig(
            min_image_width=100,
            image_quality=90,
            ocr_confidence_threshold=0.7
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_invalid(self):
        """Test validation with invalid config"""
        config = ConversionConfig(
            min_image_width=0,  # Invalid
            image_quality=150,  # Invalid
            ocr_confidence_threshold=1.5,  # Invalid
            heading_style='invalid'  # Invalid
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any('min_image_width' in e for e in errors)
        assert any('image_quality' in e for e in errors)
        assert any('ocr_confidence_threshold' in e for e in errors)
        assert any('heading_style' in e for e in errors)
    
    def test_config_to_from_yaml(self, tmp_path):
        """Test YAML serialization"""
        config = ConversionConfig(
            extract_images=False,
            min_table_rows=3,
            verbose=True
        )
        
        yaml_path = tmp_path / "config.yaml"
        config.to_yaml(yaml_path)
        
        loaded_config = ConversionConfig.from_yaml(yaml_path)
        assert loaded_config.extract_images is False
        assert loaded_config.min_table_rows == 3
        assert loaded_config.verbose is True
    
    def test_config_to_from_json(self, tmp_path):
        """Test JSON serialization"""
        config = ConversionConfig(
            extract_tables=False,
            max_hierarchy_depth=5,
            debug=True
        )
        
        json_path = tmp_path / "config.json"
        config.to_json(json_path)
        
        loaded_config = ConversionConfig.from_json(json_path)
        assert loaded_config.extract_tables is False
        assert loaded_config.max_hierarchy_depth == 5
        assert loaded_config.debug is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])