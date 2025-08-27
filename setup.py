from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pdf-to-markdown-enterprise",
    version="1.0.0",
    author="PDF to Markdown Enterprise",
    description="Enterprise-grade PDF to Markdown converter with intelligent content organization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pdf-to-markdown-enterprise",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pymupdf>=1.23.0",
        "pdfplumber>=0.10.0",
        "pypdf>=4.0.0",
        "pytesseract>=0.3.10",
        "pdf2image>=1.16.0",
        "pillow>=10.0.0",
        "spacy>=3.7.0",
        "nltk>=3.8.0",
        "markdown2>=2.4.0",
        "tabula-py>=2.8.0",
        "pandas>=2.1.0",
        "camelot-py>=0.11.0",
        "opencv-python>=4.8.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "pyyaml>=6.0.0",
        "python-slugify>=8.0.0",
        "tqdm>=4.66.0",
        "pygments>=2.17.0",
    ],
    entry_points={
        "console_scripts": [
            "pdf2md=pdf_to_markdown.cli:main",
        ],
    },
)