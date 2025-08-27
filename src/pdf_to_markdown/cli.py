import click
import logging
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import sys

from .converter import PDFToMarkdownConverter
from .config import ConversionConfig, create_example_config_file

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0', prog_name='pdf2md')
def cli():
    """
    PDF to Markdown Enterprise - Comprehensive PDF to Markdown converter
    
    Transform PDF documents into well-structured Markdown with intelligent
    content organization, image extraction, table conversion, and code detection.
    """
    pass


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.argument('output_dir', type=click.Path(path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Configuration file (YAML or JSON)')
@click.option('--images/--no-images', default=True, 
              help='Extract images from PDF')
@click.option('--tables/--no-tables', default=True,
              help='Extract tables from PDF')
@click.option('--code/--no-code', default=True,
              help='Extract code blocks from PDF')
@click.option('--ocr/--no-ocr', default=True,
              help='Use OCR for scanned pages')
@click.option('--create-folders/--no-folders', default=True,
              help='Create folder structure based on document hierarchy')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
@click.option('--debug', is_flag=True,
              help='Enable debug output')
def convert(pdf_path: Path, output_dir: Path, config: Path, 
           images: bool, tables: bool, code: bool, ocr: bool,
           create_folders: bool, verbose: bool, debug: bool):
    """Convert a single PDF file to Markdown"""
    
    # Display header
    console.print(Panel.fit(
        "[bold blue]PDF to Markdown Converter[/bold blue]\n"
        f"Converting: [green]{pdf_path.name}[/green]",
        border_style="blue"
    ))
    
    # Load or create configuration
    if config:
        console.print(f"Loading configuration from: [cyan]{config}[/cyan]")
        if config.suffix in ['.yaml', '.yml']:
            conversion_config = ConversionConfig.from_yaml(config)
        else:
            conversion_config = ConversionConfig.from_json(config)
    else:
        conversion_config = ConversionConfig(
            extract_images=images,
            extract_tables=tables,
            extract_code=code,
            use_ocr=ocr,
            create_folder_structure=create_folders,
            verbose=verbose,
            debug=debug
        )
    
    # Display configuration
    if verbose:
        _display_config(conversion_config)
    
    try:
        # Create converter
        converter = PDFToMarkdownConverter(conversion_config)
        
        # Perform conversion
        with console.status("[bold green]Converting PDF...") as status:
            result_path = converter.convert(pdf_path, output_dir)
        
        # Success message
        console.print(Panel.fit(
            f"[bold green]✓ Conversion successful![/bold green]\n"
            f"Output saved to: [cyan]{output_dir}[/cyan]\n"
            f"Main file: [cyan]{result_path}[/cyan]",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]✗ Conversion failed![/bold red]\n"
            f"Error: {str(e)}",
            border_style="red"
        ))
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, path_type=Path))
@click.argument('output_dir', type=click.Path(path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Configuration file (YAML or JSON)')
@click.option('--pattern', '-p', default='*.pdf',
              help='File pattern to match PDFs (default: *.pdf)')
@click.option('--parallel/--sequential', default=True,
              help='Process files in parallel')
@click.option('--workers', '-w', type=int, default=4,
              help='Number of parallel workers')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def batch(input_dir: Path, output_dir: Path, config: Path, 
         pattern: str, parallel: bool, workers: int, verbose: bool):
    """Convert multiple PDF files in batch"""
    
    # Find PDF files
    pdf_files = list(input_dir.glob(pattern))
    
    if not pdf_files:
        console.print(f"[yellow]No PDF files found matching pattern: {pattern}[/yellow]")
        return
    
    # Display header
    console.print(Panel.fit(
        "[bold blue]Batch PDF to Markdown Conversion[/bold blue]\n"
        f"Found [green]{len(pdf_files)}[/green] PDF files",
        border_style="blue"
    ))
    
    # Load configuration
    if config:
        if config.suffix in ['.yaml', '.yml']:
            conversion_config = ConversionConfig.from_yaml(config)
        else:
            conversion_config = ConversionConfig.from_json(config)
    else:
        conversion_config = ConversionConfig(
            parallel_processing=parallel,
            num_workers=workers,
            verbose=verbose
        )
    
    try:
        # Create converter
        converter = PDFToMarkdownConverter(conversion_config)
        
        # Perform batch conversion
        results = converter.batch_convert(pdf_files, output_dir)
        
        # Display results
        _display_batch_results(results)
        
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]✗ Batch conversion failed![/bold red]\n"
            f"Error: {str(e)}",
            border_style="red"
        ))
        sys.exit(1)


@cli.command()
@click.argument('output_path', type=click.Path(path_type=Path))
@click.option('--format', '-f', type=click.Choice(['yaml', 'json']), default='yaml',
              help='Configuration file format')
def init_config(output_path: Path, format: str):
    """Create an example configuration file"""
    
    if format == 'json':
        output_path = output_path.with_suffix('.json')
    else:
        output_path = output_path.with_suffix('.yaml')
    
    try:
        created_path = create_example_config_file(output_path)
        
        console.print(Panel.fit(
            f"[bold green]✓ Configuration file created![/bold green]\n"
            f"File: [cyan]{created_path}[/cyan]\n\n"
            f"Edit this file to customize your conversion settings,\n"
            f"then use it with: [yellow]pdf2md convert -c {created_path} <pdf> <output>[/yellow]",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[bold red]Failed to create configuration file:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
def analyze(pdf_path: Path):
    """Analyze PDF structure without conversion"""
    
    console.print(Panel.fit(
        "[bold blue]PDF Structure Analysis[/bold blue]\n"
        f"Analyzing: [green]{pdf_path.name}[/green]",
        border_style="blue"
    ))
    
    try:
        # Create minimal config for analysis
        config = ConversionConfig(verbose=True)
        converter = PDFToMarkdownConverter(config)
        
        with console.status("[bold green]Analyzing PDF...") as status:
            # Extract content
            content = converter._extract_content(pdf_path)
            
            # Analyze structure
            structure = converter._analyze_structure(content)
        
        # Display analysis results
        _display_analysis(content, structure)
        
    except Exception as e:
        console.print(f"[bold red]Analysis failed:[/bold red] {e}")
        sys.exit(1)


def _display_config(config: ConversionConfig):
    """Display configuration settings"""
    table = Table(title="Configuration Settings", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Extract Images", str(config.extract_images))
    table.add_row("Extract Tables", str(config.extract_tables))
    table.add_row("Extract Code", str(config.extract_code))
    table.add_row("Use OCR", str(config.use_ocr))
    table.add_row("Create Folders", str(config.create_folder_structure))
    table.add_row("Table Method", config.table_extraction_method)
    table.add_row("Heading Style", config.heading_style)
    
    console.print(table)


def _display_batch_results(results):
    """Display batch conversion results"""
    table = Table(title="Batch Conversion Results", show_header=True)
    table.add_column("PDF File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Output/Error")
    
    successful = 0
    for pdf_path, result, error in results:
        if result:
            table.add_row(pdf_path.name, "[green]✓ Success[/green]", str(result))
            successful += 1
        else:
            table.add_row(pdf_path.name, "[red]✗ Failed[/red]", str(error))
    
    console.print(table)
    console.print(f"\nSummary: [green]{successful}[/green]/{len(results)} successful")


def _display_analysis(content, structure):
    """Display PDF analysis results"""
    
    # Content statistics
    stats_table = Table(title="Content Statistics", show_header=True)
    stats_table.add_column("Type", style="cyan")
    stats_table.add_column("Count", style="green")
    
    stats_table.add_row("Text Blocks", str(len(content.get('text_blocks', []))))
    stats_table.add_row("Images", str(len(content.get('images', []))))
    stats_table.add_row("Tables", str(len(content.get('tables', []))))
    stats_table.add_row("Code Blocks", str(len(content.get('code_blocks', []))))
    
    console.print(stats_table)
    
    # Document structure
    console.print("\n[bold]Document Structure:[/bold]")
    _print_structure_tree(structure)


def _print_structure_tree(node, indent=0):
    """Print document structure as tree"""
    if hasattr(node, 'title'):
        prefix = "  " * indent + ("├─ " if indent > 0 else "")
        console.print(f"{prefix}[cyan]{node.title}[/cyan]")
        
    for child in getattr(node, 'children', []):
        _print_structure_tree(child, indent + 1)


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()