import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pdfplumber
import tabula
from dataclasses import dataclass
from pathlib import Path
import re

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents an extracted table with metadata"""
    data: pd.DataFrame
    page_num: int
    bbox: tuple
    caption: Optional[str] = None
    headers: Optional[List[str]] = None
    table_type: str = "data"  # data, comparison, summary, etc.


class TableExtractor:
    """Extract and process tables from PDF files"""
    
    def __init__(self, method: str = "auto", min_rows: int = 2, min_cols: int = 2):
        self.method = method  # auto, pdfplumber, tabula, camelot
        self.min_rows = min_rows
        self.min_cols = min_cols
        
    def extract(self, pdf_path: Path) -> List[ExtractedTable]:
        """Extract all tables from PDF"""
        tables = []
        
        if self.method == "auto":
            # Try multiple methods and combine results
            tables.extend(self._extract_with_pdfplumber(pdf_path))
            
            if not tables:
                tables.extend(self._extract_with_tabula(pdf_path))
                
            if not tables:
                tables.extend(self._extract_with_camelot(pdf_path))
        elif self.method == "pdfplumber":
            tables = self._extract_with_pdfplumber(pdf_path)
        elif self.method == "tabula":
            tables = self._extract_with_tabula(pdf_path)
        elif self.method == "camelot":
            tables = self._extract_with_camelot(pdf_path)
            
        # Filter and clean tables
        tables = self._filter_valid_tables(tables)
        tables = self._clean_tables(tables)
        tables = self._classify_tables(tables)
        
        return tables
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> List[ExtractedTable]:
        """Extract tables using pdfplumber"""
        extracted_tables = []
        
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    
                    for table_data in page_tables:
                        if table_data and len(table_data) >= self.min_rows:
                            # Convert to DataFrame
                            df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            
                            if len(df.columns) >= self.min_cols:
                                extracted_tables.append(ExtractedTable(
                                    data=df,
                                    page_num=page_num,
                                    bbox=(0, 0, page.width, page.height),
                                    headers=list(df.columns)
                                ))
                                
        except Exception as e:
            logger.warning(f"PDFPlumber table extraction failed: {e}")
            
        return extracted_tables
    
    def _extract_with_tabula(self, pdf_path: Path) -> List[ExtractedTable]:
        """Extract tables using tabula-py"""
        extracted_tables = []
        
        try:
            # Read tables from all pages
            dfs = tabula.read_pdf(
                str(pdf_path),
                pages='all',
                multiple_tables=True,
                pandas_options={'header': 0}
            )
            
            # Get page information for each table
            for i, df in enumerate(dfs):
                if len(df) >= self.min_rows and len(df.columns) >= self.min_cols:
                    # Try to determine page number (tabula doesn't provide this directly)
                    page_num = i + 1  # Approximate
                    
                    extracted_tables.append(ExtractedTable(
                        data=df,
                        page_num=page_num,
                        bbox=(0, 0, 0, 0),  # Tabula doesn't provide bbox
                        headers=list(df.columns)
                    ))
                    
        except Exception as e:
            logger.warning(f"Tabula table extraction failed: {e}")
            
        return extracted_tables
    
    def _extract_with_camelot(self, pdf_path: Path) -> List[ExtractedTable]:
        """Extract tables using camelot-py"""
        extracted_tables = []
        
        try:
            import camelot
            
            # Read tables from all pages
            tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='stream')
            
            for table in tables:
                df = table.df
                
                if len(df) >= self.min_rows and len(df.columns) >= self.min_cols:
                    # Use first row as headers
                    df.columns = df.iloc[0]
                    df = df[1:].reset_index(drop=True)
                    
                    extracted_tables.append(ExtractedTable(
                        data=df,
                        page_num=table.page,
                        bbox=table._bbox if hasattr(table, '_bbox') else (0, 0, 0, 0),
                        headers=list(df.columns)
                    ))
                    
        except ImportError:
            logger.warning("Camelot not installed. Install with: pip install camelot-py[cv]")
        except Exception as e:
            logger.warning(f"Camelot table extraction failed: {e}")
            
        return extracted_tables
    
    def _filter_valid_tables(self, tables: List[ExtractedTable]) -> List[ExtractedTable]:
        """Filter out invalid or low-quality tables"""
        valid_tables = []
        
        for table in tables:
            # Check if table has actual data
            if table.data.empty:
                continue
                
            # Check for minimum non-null values
            non_null_ratio = table.data.notna().sum().sum() / (len(table.data) * len(table.data.columns))
            if non_null_ratio < 0.3:  # Less than 30% non-null values
                continue
                
            # Check if it's not just a list (single column)
            if len(table.data.columns) < self.min_cols:
                continue
                
            valid_tables.append(table)
            
        return valid_tables
    
    def _clean_tables(self, tables: List[ExtractedTable]) -> List[ExtractedTable]:
        """Clean and normalize table data"""
        for table in tables:
            # Clean column names
            table.data.columns = [self._clean_text(str(col)) for col in table.data.columns]
            
            # Clean cell values
            for col in table.data.columns:
                table.data[col] = table.data[col].apply(lambda x: self._clean_text(str(x)) if pd.notna(x) else '')
                
            # Remove empty rows
            table.data = table.data[table.data.apply(lambda row: any(row != ''), axis=1)]
            
            # Remove empty columns
            table.data = table.data.loc[:, table.data.apply(lambda col: any(col != ''), axis=0)]
            
            # Update headers
            table.headers = list(table.data.columns)
            
        return tables
    
    def _clean_text(self, text: str) -> str:
        """Clean text content"""
        if not text or text.lower() in ['nan', 'none']:
            return ''
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters that might break markdown
        text = text.replace('|', '\\|')
        
        return text
    
    def _classify_tables(self, tables: List[ExtractedTable]) -> List[ExtractedTable]:
        """Classify tables by type based on content"""
        for table in tables:
            # Check for numerical data
            numeric_cols = 0
            for col in table.data.columns:
                try:
                    pd.to_numeric(table.data[col], errors='coerce').notna().sum()
                    if pd.to_numeric(table.data[col], errors='coerce').notna().sum() > len(table.data) * 0.5:
                        numeric_cols += 1
                except:
                    pass
                    
            numeric_ratio = numeric_cols / len(table.data.columns) if len(table.data.columns) > 0 else 0
            
            # Classify based on content
            if numeric_ratio > 0.7:
                table.table_type = "numerical"
            elif numeric_ratio > 0.3:
                table.table_type = "mixed"
            elif len(table.data.columns) == 2:
                table.table_type = "key-value"
            elif any(keyword in ' '.join(table.headers).lower() for keyword in ['total', 'sum', 'average', 'mean']):
                table.table_type = "summary"
            else:
                table.table_type = "data"
                
        return tables
    
    def tables_to_markdown(self, tables: List[ExtractedTable]) -> List[str]:
        """Convert tables to Markdown format"""
        markdown_tables = []
        
        for table in tables:
            md = self._dataframe_to_markdown(table.data, table.caption)
            markdown_tables.append(md)
            
        return markdown_tables
    
    def _dataframe_to_markdown(self, df: pd.DataFrame, caption: Optional[str] = None) -> str:
        """Convert DataFrame to Markdown table"""
        lines = []
        
        # Add caption if provided
        if caption:
            lines.append(f"**{caption}**\n")
            
        # Header row
        headers = '| ' + ' | '.join(str(col) for col in df.columns) + ' |'
        lines.append(headers)
        
        # Separator row
        separator = '| ' + ' | '.join(['---' for _ in df.columns]) + ' |'
        lines.append(separator)
        
        # Data rows
        for _, row in df.iterrows():
            row_str = '| ' + ' | '.join(str(val) for val in row) + ' |'
            lines.append(row_str)
            
        return '\n'.join(lines)
    
    def export_tables(self, tables: List[ExtractedTable], output_dir: Path, 
                     formats: List[str] = ['csv', 'json', 'markdown']) -> Dict[str, Dict[str, Path]]:
        """Export tables to various formats"""
        output_dir.mkdir(parents=True, exist_ok=True)
        exported_paths = {}
        
        for i, table in enumerate(tables):
            paths = {}
            base_name = f"table_page{table.page_num:03d}_{i+1:02d}"
            
            if 'csv' in formats:
                csv_path = output_dir / f"{base_name}.csv"
                table.data.to_csv(csv_path, index=False)
                paths['csv'] = csv_path
                
            if 'json' in formats:
                json_path = output_dir / f"{base_name}.json"
                table.data.to_json(json_path, orient='records', indent=2)
                paths['json'] = json_path
                
            if 'markdown' in formats:
                md_path = output_dir / f"{base_name}.md"
                md_content = self._dataframe_to_markdown(table.data, table.caption)
                md_path.write_text(md_content, encoding='utf-8')
                paths['markdown'] = md_path
                
            if 'excel' in formats:
                excel_path = output_dir / f"{base_name}.xlsx"
                table.data.to_excel(excel_path, index=False)
                paths['excel'] = excel_path
                
            exported_paths[id(table)] = paths
            
        return exported_paths