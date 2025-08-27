import logging
from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass
from pathlib import Path
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

logger = logging.getLogger(__name__)


@dataclass
class CodeBlock:
    """Represents an extracted code block"""
    content: str
    language: Optional[str]
    page_num: int
    start_line: int
    end_line: int
    confidence: float = 1.0
    block_type: str = "snippet"  # snippet, function, class, script, example


class CodeBlockExtractor:
    """Extract and classify code blocks from text content"""
    
    def __init__(self):
        self.code_patterns = {
            'python': [
                re.compile(r'^(def|class|import|from|if __name__)', re.MULTILINE),
                re.compile(r'^\s*(print|return|raise|yield|async def|await)', re.MULTILINE),
            ],
            'javascript': [
                re.compile(r'^(function|const|let|var|class|import|export)', re.MULTILINE),
                re.compile(r'(=>|\$\(|document\.|console\.)', re.MULTILINE),
            ],
            'java': [
                re.compile(r'^(public|private|protected|class|interface|import)', re.MULTILINE),
                re.compile(r'(System\.out\.|public static void main)', re.MULTILINE),
            ],
            'c': [
                re.compile(r'^#include\s*<.*>', re.MULTILINE),
                re.compile(r'(int main\(|printf\(|scanf\()', re.MULTILINE),
            ],
            'cpp': [
                re.compile(r'^#include\s*<.*>', re.MULTILINE),
                re.compile(r'(std::|cout|cin|using namespace)', re.MULTILINE),
            ],
            'csharp': [
                re.compile(r'^(using|namespace|public|private|class)', re.MULTILINE),
                re.compile(r'(Console\.|static void Main)', re.MULTILINE),
            ],
            'sql': [
                re.compile(r'\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|DROP)\b', re.IGNORECASE),
                re.compile(r'\b(JOIN|GROUP BY|ORDER BY|HAVING)\b', re.IGNORECASE),
            ],
            'bash': [
                re.compile(r'^#!/bin/(bash|sh)', re.MULTILINE),
                re.compile(r'(\$\{|\$\(|echo|export|if \[)', re.MULTILINE),
            ],
            'yaml': [
                re.compile(r'^[a-zA-Z_-]+:\s*', re.MULTILINE),
                re.compile(r'^\s*-\s+\w+', re.MULTILINE),
            ],
            'json': [
                re.compile(r'^\s*\{[\s\S]*\}\s*$'),
                re.compile(r'"[^"]+"\s*:\s*["{[]'),
            ],
            'xml': [
                re.compile(r'^<\?xml', re.MULTILINE),
                re.compile(r'<[a-zA-Z]+[^>]*>.*</[a-zA-Z]+>', re.MULTILINE),
            ],
            'html': [
                re.compile(r'<!DOCTYPE html|<html|<head|<body', re.IGNORECASE),
                re.compile(r'<(div|span|p|h[1-6]|table|form)', re.IGNORECASE),
            ],
            'css': [
                re.compile(r'[.#]?[a-zA-Z-]+\s*\{[^}]*\}'),
                re.compile(r'(color:|background:|margin:|padding:|display:)'),
            ],
            'rust': [
                re.compile(r'\b(fn|let|mut|impl|trait|struct|enum|use)\b'),
                re.compile(r'(println!|Vec::|Option::|Result::)'),
            ],
            'go': [
                re.compile(r'^(package|import|func|type|var|const)', re.MULTILINE),
                re.compile(r'(fmt\.|func main\(\))'),
            ],
            'swift': [
                re.compile(r'\b(func|class|struct|enum|var|let|import)\b'),
                re.compile(r'(print\(|@objc|override func)'),
            ],
            'kotlin': [
                re.compile(r'\b(fun|class|val|var|import|package)\b'),
                re.compile(r'(println\(|companion object)'),
            ],
            'ruby': [
                re.compile(r'^(class|def|module|require|include)', re.MULTILINE),
                re.compile(r'(puts|gets|end$)', re.MULTILINE),
            ],
            'php': [
                re.compile(r'<\?php|\$[a-zA-Z_]'),
                re.compile(r'(echo|print|function|class)\s'),
            ],
            'r': [
                re.compile(r'<-|->|\|>'),
                re.compile(r'\b(library|function|if|else|for|while)\s*\('),
            ],
            'matlab': [
                re.compile(r'\b(function|end|if|else|for|while)\b'),
                re.compile(r'(plot\(|disp\(|zeros\(|ones\()'),
            ],
        }
        
        # Common code indicators
        self.general_code_patterns = [
            re.compile(r'^\s*(//|#|/\*|\*/)', re.MULTILINE),  # Comments
            re.compile(r'[{}\[\]();]'),  # Common code punctuation
            re.compile(r'\b(if|else|for|while|return|break|continue)\b'),  # Control flow
            re.compile(r'[=!<>]=|&&|\|\||!='),  # Operators
            re.compile(r'^\s{4,}|\t', re.MULTILINE),  # Indentation
        ]
        
    def extract(self, text_blocks: List[Any]) -> List[CodeBlock]:
        """Extract code blocks from text content"""
        code_blocks = []
        
        for block in text_blocks:
            if hasattr(block, 'content'):
                content = block.content
                page_num = getattr(block, 'page_num', 1)
                
                # Check if block contains code
                if self._is_code_block(content):
                    # Try to detect language
                    language = self._detect_language(content)
                    
                    # Extract individual code segments
                    segments = self._extract_code_segments(content)
                    
                    for seg_content, start_line, end_line in segments:
                        code_block = CodeBlock(
                            content=seg_content,
                            language=language,
                            page_num=page_num,
                            start_line=start_line,
                            end_line=end_line,
                            confidence=self._calculate_confidence(seg_content, language)
                        )
                        
                        # Classify code block type
                        code_block.block_type = self._classify_code_type(seg_content, language)
                        
                        code_blocks.append(code_block)
                        
        return code_blocks
    
    def _is_code_block(self, text: str) -> bool:
        """Determine if text contains code"""
        if not text or len(text.strip()) < 10:
            return False
            
        # Count code indicators
        indicators = 0
        
        # Check for general code patterns
        for pattern in self.general_code_patterns:
            if pattern.search(text):
                indicators += 1
                
        # Check for language-specific patterns
        for patterns in self.code_patterns.values():
            for pattern in patterns:
                if pattern.search(text):
                    indicators += 2
                    break
                    
        # Consider it code if we have enough indicators
        return indicators >= 3
    
    def _detect_language(self, code: str) -> Optional[str]:
        """Detect programming language of code"""
        # First try pattern-based detection
        best_match = None
        best_score = 0
        
        for lang, patterns in self.code_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(code):
                    score += 1
                    
            if score > best_score:
                best_score = score
                best_match = lang
                
        if best_match and best_score >= 2:
            return best_match
            
        # Fallback to Pygments lexer guessing
        try:
            lexer = guess_lexer(code)
            return lexer.aliases[0] if lexer.aliases else None
        except ClassNotFound:
            pass
            
        return None
    
    def _extract_code_segments(self, text: str) -> List[Tuple[str, int, int]]:
        """Extract individual code segments from text"""
        segments = []
        lines = text.split('\n')
        
        # Look for continuous blocks of code-like content
        current_segment = []
        start_line = 0
        in_code = False
        
        for i, line in enumerate(lines):
            # Check if line looks like code
            is_code_line = self._is_code_line(line)
            
            if is_code_line:
                if not in_code:
                    in_code = True
                    start_line = i
                current_segment.append(line)
            else:
                if in_code and len(current_segment) > 1:
                    # End of code segment
                    segment_text = '\n'.join(current_segment)
                    segments.append((segment_text, start_line, i - 1))
                    current_segment = []
                in_code = False
                
        # Handle last segment
        if current_segment and len(current_segment) > 1:
            segment_text = '\n'.join(current_segment)
            segments.append((segment_text, start_line, len(lines) - 1))
            
        return segments
    
    def _is_code_line(self, line: str) -> bool:
        """Check if a single line looks like code"""
        stripped = line.strip()
        
        # Empty lines in code blocks
        if not stripped and line.startswith((' ', '\t')):
            return True
            
        # Indented lines
        if line.startswith((' ' * 4, '\t')):
            return True
            
        # Lines with code characteristics
        code_chars = ['{', '}', '(', ')', '[', ']', ';', '=', '->', '=>', '::', '//']
        return any(char in line for char in code_chars)
    
    def _calculate_confidence(self, code: str, language: Optional[str]) -> float:
        """Calculate confidence score for code detection"""
        confidence = 0.5
        
        # Increase confidence if language was detected
        if language:
            confidence += 0.2
            
            # Check if code matches detected language patterns
            if language in self.code_patterns:
                matches = sum(1 for p in self.code_patterns[language] if p.search(code))
                confidence += min(0.3, matches * 0.1)
                
        # Check code structure
        lines = code.split('\n')
        if len(lines) > 3:
            confidence += 0.1
            
        # Check for consistent indentation
        indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
        if indents and len(set(indents)) / len(indents) < 0.5:  # Consistent indentation
            confidence += 0.1
            
        return min(1.0, confidence)
    
    def _classify_code_type(self, code: str, language: Optional[str]) -> str:
        """Classify the type of code block"""
        lines = code.split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # Check for complete script markers
        if language in ['bash', 'python'] and first_line.startswith('#!'):
            return "script"
            
        # Check for class definitions
        if re.search(r'\b(class|interface|struct)\s+\w+', code):
            return "class"
            
        # Check for function definitions
        if re.search(r'\b(def|function|func|fn)\s+\w+', code):
            return "function"
            
        # Check for import statements (likely example/snippet)
        if re.search(r'^(import|from|using|include)', code, re.MULTILINE):
            if len(lines) > 10:
                return "example"
                
        # Check for SQL queries
        if language == 'sql' or re.search(r'\b(SELECT|INSERT|UPDATE|DELETE)\b', code, re.IGNORECASE):
            return "query"
            
        # Check for configuration files
        if language in ['yaml', 'json', 'xml', 'ini']:
            return "config"
            
        # Default to snippet for small code blocks
        return "snippet" if len(lines) < 10 else "example"
    
    def format_code_block(self, code_block: CodeBlock, add_line_numbers: bool = False) -> str:
        """Format code block for display/export"""
        content = code_block.content
        
        if add_line_numbers:
            lines = content.split('\n')
            numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            content = '\n'.join(numbered_lines)
            
        return content
    
    def export_code_blocks(self, code_blocks: List[CodeBlock], output_dir: Path) -> Dict[CodeBlock, Path]:
        """Export code blocks to separate files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        exported_paths = {}
        
        # Group by language
        language_counts = {}
        
        for block in code_blocks:
            lang = block.language or 'unknown'
            if lang not in language_counts:
                language_counts[lang] = 0
            language_counts[lang] += 1
            
            # Determine file extension
            extensions = {
                'python': '.py',
                'javascript': '.js',
                'java': '.java',
                'c': '.c',
                'cpp': '.cpp',
                'csharp': '.cs',
                'sql': '.sql',
                'bash': '.sh',
                'yaml': '.yml',
                'json': '.json',
                'xml': '.xml',
                'html': '.html',
                'css': '.css',
                'rust': '.rs',
                'go': '.go',
                'swift': '.swift',
                'kotlin': '.kt',
                'ruby': '.rb',
                'php': '.php',
                'r': '.r',
                'matlab': '.m',
            }
            
            ext = extensions.get(lang, '.txt')
            filename = f"{lang}_{block.block_type}_{language_counts[lang]:03d}{ext}"
            filepath = output_dir / filename
            
            # Write code to file
            filepath.write_text(block.content, encoding='utf-8')
            exported_paths[block] = filepath
            
            logger.info(f"Exported {block.block_type} code block to {filepath}")
            
        return exported_paths