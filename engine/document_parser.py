"""
Document Parser Module for ClauseGuard Engine.

Provides the DocumentParser class that handles extraction of text content
from PDF, DOCX, and TXT file formats, returning structured metadata
alongside the extracted text.
"""

import os
from typing import Dict, Callable

from PyPDF2 import PdfReader
from docx import Document


class DocumentParser:
    """Parses PDF, DOCX, and TXT documents and returns extracted text with metadata.

    Supports three common document formats used in legal and contract
    workflows. Each parser returns clean, normalized text suitable for
    downstream NLP processing.

    Usage:
        result = DocumentParser.parse('contract.pdf')
        print(result['text'])
        print(result['word_count'])
    """

    SUPPORTED_EXTENSIONS: set = {'.pdf', '.docx', '.txt'}

    @staticmethod
    def parse(file_path: str) -> Dict[str, object]:
        """Parse a document and return its text content and metadata.

        Args:
            file_path: Absolute or relative path to the document file.

        Returns:
            A dict containing:
                - text (str): The full extracted text.
                - filename (str): The base filename.
                - extension (str): The lowercase file extension.
                - char_count (int): Total character count of the text.
                - word_count (int): Total word count of the text.

        Raises:
            ValueError: If the file extension is not in SUPPORTED_EXTENSIONS.
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f'File not found: {file_path}')

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in DocumentParser.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f'Unsupported file type: {ext}. '
                f'Supported types: {", ".join(sorted(DocumentParser.SUPPORTED_EXTENSIONS))}'
            )

        parsers: Dict[str, Callable[[str], str]] = {
            '.pdf': DocumentParser._parse_pdf,
            '.docx': DocumentParser._parse_docx,
            '.txt': DocumentParser._parse_txt,
        }

        text = parsers[ext](file_path)

        return {
            'text': text,
            'filename': os.path.basename(file_path),
            'extension': ext,
            'char_count': len(text),
            'word_count': len(text.split()),
        }

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """Extract text from a PDF file using PyPDF2.

        Iterates through all pages and joins non-empty page texts
        with double newlines for paragraph separation.
        """
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
        return '\n\n'.join(pages)

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        """Extract text from a DOCX file using python-docx.

        Reads all paragraphs, strips whitespace, and joins non-empty
        paragraphs with double newlines.
        """
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return '\n\n'.join(paragraphs)

    @staticmethod
    def _parse_txt(file_path: str) -> str:
        """Read text from a plain text file.

        Uses UTF-8 encoding with error ignoring to handle
        non-standard characters gracefully.
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
