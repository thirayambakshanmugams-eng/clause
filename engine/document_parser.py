"""
Document Parser Module for ClauseGuard Engine.

Provides the DocumentParser class that handles extraction of text content
from PDF, DOCX, and TXT file formats, returning structured metadata
alongside the extracted text.
"""

import os
import re
import csv
import tempfile
import time
import zipfile
import shutil
from typing import Dict, Callable, Optional

from PyPDF2 import PdfReader
from docx import Document


class DocumentParser:
    """Parses PDF, DOCX, DOC, RTF, ODT, CSV, TXT, MD, PNG, JPG, and JPEG documents and returns extracted text with metadata."""

    SUPPORTED_EXTENSIONS: set = {
        '.pdf', '.docx', '.doc', '.rtf', '.odt', '.csv', '.md',
        '.txt', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'
    }

    @staticmethod
    def parse(file_path: str, api_key: Optional[str] = None) -> Dict[str, object]:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f'File not found: {file_path}')

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in DocumentParser.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f'Unsupported file type: {ext}. '
                f'Supported types: {", ".join(sorted(DocumentParser.SUPPORTED_EXTENSIONS))}'
            )

        if ext == '.pdf':
            text = DocumentParser._parse_pdf(file_path, api_key=api_key)
        elif ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'):
            text = DocumentParser._parse_image(file_path, api_key=api_key)
        elif ext == '.docx':
            text = DocumentParser._parse_docx(file_path, api_key=api_key)
        elif ext == '.doc':
            text = DocumentParser._parse_doc(file_path)
        elif ext == '.rtf':
            text = DocumentParser._parse_rtf(file_path)
        elif ext == '.odt':
            text = DocumentParser._parse_odt(file_path)
        elif ext == '.csv':
            text = DocumentParser._parse_csv(file_path)
        else:
            text = DocumentParser._parse_txt(file_path)

        return {
            'text': text,
            'filename': os.path.basename(file_path),
            'extension': ext,
            'char_count': len(text),
            'word_count': len(text.split()),
        }

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        extracted = ""
        try:
            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    pages.append(page_text.strip())
            extracted = '\n\n'.join(pages)
        except Exception:
            extracted = ""

        if extracted.strip():
            return extracted

        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        pages.append(page_text.strip())
                extracted = '\n\n'.join(pages)
        except Exception:
            pass

        return extracted

    @staticmethod
    def _locate_local_ocr_tools() -> tuple[Optional[str], Optional[str]]:
        tesseract_path = shutil.which('tesseract')
        poppler_bin_dir = None

        if not tesseract_path:
            for candidate in (
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ):
                if os.path.exists(candidate):
                    tesseract_path = candidate
                    break

        pdfinfo_path = shutil.which('pdfinfo')
        if pdfinfo_path:
            poppler_bin_dir = os.path.dirname(pdfinfo_path)
        else:
            for candidate in (
                os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin'),
                r'C:\Program Files\Poppler\bin',
                r'C:\Program Files (x86)\Poppler\bin',
            ):
                if os.path.exists(os.path.join(candidate, 'pdfinfo.exe')):
                    poppler_bin_dir = candidate
                    break

        return tesseract_path, poppler_bin_dir

    @staticmethod
    def _ensure_local_ocr_paths() -> tuple[Optional[str], Optional[str]]:
        tesseract_path, poppler_bin_dir = DocumentParser._locate_local_ocr_tools()
        if tesseract_path and not shutil.which('tesseract'):
            os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + os.path.dirname(tesseract_path)
        if poppler_bin_dir and not shutil.which('pdfinfo'):
            os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + poppler_bin_dir
        return tesseract_path, poppler_bin_dir

    @staticmethod
    def _local_pdf_ocr(file_path: str) -> tuple[str, bool]:
        available = False
        try:
            import pdfplumber
            available = True
            pages = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        pages.append(text.strip())
            if pages:
                return '\n\n'.join(pages), True
        except ModuleNotFoundError:
            return '', False
        except Exception:
            pass

        tesseract_path, poppler_bin_dir = DocumentParser._ensure_local_ocr_paths()
        try:
            from pdf2image import convert_from_path
            import pytesseract
            from PIL import Image
            available = True

            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path

            convert_kwargs = {'dpi': 300}
            if poppler_bin_dir:
                convert_kwargs['poppler_path'] = poppler_bin_dir

            images = convert_from_path(file_path, **convert_kwargs)
            pages = []
            for image in images:
                page_text = pytesseract.image_to_string(image)
                if page_text and page_text.strip():
                    pages.append(page_text.strip())
            return '\n\n'.join(pages), True
        except ModuleNotFoundError:
            return '', False
        except Exception:
            pass

        return '', available

    @staticmethod
    def _parse_pdf(file_path: str, api_key: Optional[str] = None) -> str:
        """Extract text from a PDF file using PyPDF2, with Gemini OCR fallback for scanned PDFs."""
        extracted = DocumentParser._extract_pdf_text(file_path)
        empty_pages = 0
        total_pages = 0

        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            for page in reader.pages:
                text = page.extract_text()
                if not text or not text.strip():
                    empty_pages += 1
        except Exception:
            total_pages = 0

        sparse_text = len(extracted.strip()) < 20
        has_image_pages = total_pages > 0 and empty_pages > 0
        low_density = total_pages > 0 and len(extracted.strip()) / total_pages < 50

        if sparse_text or has_image_pages or low_density:
            ocr_text = ''
            local_available = False

            if api_key or os.environ.get('GEMINI_API_KEY'):
                ocr_text = DocumentParser._gemini_ocr(file_path, api_key=api_key)

            if not ocr_text.strip():
                ocr_text, local_available = DocumentParser._local_pdf_ocr(file_path)

            if ocr_text.strip():
                if extracted.strip() and len(ocr_text.strip()) > len(extracted.strip()):
                    return ocr_text
                if extracted.strip() and ocr_text.strip() not in extracted:
                    return f"{extracted}\n\n{ocr_text}".strip()
                return ocr_text

            if not (api_key or os.environ.get('GEMINI_API_KEY')):
                if not local_available:
                    raise ValueError(
                        'Scanned or image-only PDF detected. OCR is required to extract text from this file. '
                        'Install Tesseract OCR and the python packages pdf2image, pytesseract, and Pillow, or configure a Gemini API key.'
                    )
                raise ValueError(
                    'Scanned or image-only PDF detected. Local OCR was attempted but did not extract any text. '
                    'Try a different file or configure a Gemini API key for OCR.'
                )

            if not local_available:
                raise ValueError(
                    'Could not extract text from the PDF. The OCR service did not return any text, and local OCR prerequisites are missing. '
                    'Install Tesseract OCR and the python packages pdf2image, pytesseract, and Pillow.'
                )

            raise ValueError('Could not extract text from the PDF. The OCR service did not return any text.')

        return extracted

    @staticmethod
    def _parse_doc(file_path: str) -> str:
        try:
            import subprocess
            text = subprocess.check_output(['antiword', file_path], stderr=subprocess.DEVNULL)
            return text.decode('utf-8', errors='ignore')
        except FileNotFoundError:
            raise ValueError(
                'DOC file support requires antiword. Install antiword or convert the file to DOCX/PDF/TXT and try again.'
            )
        except Exception:
            raise ValueError('Unable to extract text from DOC file. Convert it to DOCX, PDF, or TXT and try again.')

    @staticmethod
    def _parse_rtf(file_path: str) -> str:
        with open(file_path, 'rb') as f:
            raw = f.read().decode('utf-8', errors='ignore')
        raw = raw.replace('\\par', '\n').replace('\\line', '\n')
        raw = re.sub(r"\\'[0-9a-fA-F]{2}", ' ', raw)
        raw = re.sub(r'\\[a-zA-Z]+\d* ?', '', raw)
        raw = re.sub(r'[{}]', '', raw)
        return re.sub(r'\n\s*\n+', '\n\n', raw).strip()

    @staticmethod
    def _parse_odt(file_path: str) -> str:
        try:
            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                xml_bytes = docx_zip.read('content.xml')
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_bytes)
            texts = [elem.text for elem in root.iter() if elem.text]
            return '\n'.join(t.strip() for t in texts if t.strip())
        except Exception:
            raise ValueError('Unable to extract text from ODT file. Convert it to TXT, PDF, or DOCX and try again.')

    @staticmethod
    def _parse_csv(file_path: str) -> str:
        rows = []
        try:
            with open(file_path, newline='', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    line = ' '.join(cell.strip() for cell in row if cell.strip())
                    if line:
                        rows.append(line)
        except Exception:
            raise ValueError('Unable to extract text from CSV file.')
        return '\n'.join(rows)

    @staticmethod
    def _parse_image(file_path: str, api_key: Optional[str] = None) -> str:
        """Transcribe text from image files using OCR."""
        if api_key or os.environ.get('GEMINI_API_KEY'):
            return DocumentParser._gemini_ocr(file_path, api_key=api_key)

        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(file_path)).strip()
        except ModuleNotFoundError:
            raise ValueError(
                'Image text extraction requires OCR. Please configure a Gemini API key in API Settings or install pytesseract.'
            )
        except Exception:
            raise ValueError(
                'Unable to extract text from the image. Please ensure the file is a valid image or provide a Gemini API key for OCR.'
            )

    @staticmethod
    def _wait_for_gemini_file(genai, uploaded_file, timeout: int = 120):
        """Wait until an uploaded Gemini file is ready for content generation."""
        start = time.time()
        file = uploaded_file
        while file.state.name == "PROCESSING":
            if time.time() - start > timeout:
                raise TimeoutError("Gemini file processing timed out")
            time.sleep(2)
            file = genai.get_file(file.name)
        if file.state.name != "ACTIVE":
            raise ValueError(f"Gemini file not ready: {file.state.name}")
        return file

    @staticmethod
    def _gemini_ocr(file_path: str, api_key: Optional[str] = None) -> str:
        """Upload file to Gemini 2.0 Flash for intelligent OCR document transcription."""
        key = api_key or os.environ.get('GEMINI_API_KEY')
        if not key:
            return ""

        uploaded_file = None
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            uploaded_file = genai.upload_file(file_path)
            uploaded_file = DocumentParser._wait_for_gemini_file(genai, uploaded_file)
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = (
                "Extract and transcribe all text from this contract or legal document image/PDF exactly as written. "
                "Output only the clean extracted document text with original headings and clause formatting. Do not add intro or summary comments."
            )
            response = model.generate_content([uploaded_file, prompt])
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[DocumentParser OCR Warning] {e}")
        finally:
            if uploaded_file is not None:
                try:
                    import google.generativeai as genai
                    genai.delete_file(uploaded_file.name)
                except Exception:
                    pass

        return ""

    @staticmethod
    def _parse_docx(file_path: str, api_key: Optional[str] = None) -> str:
        doc = Document(file_path)
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        parts.append(cell_text)

        text = '\n\n'.join(parts)
        image_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp')
        image_texts = []

        try:
            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                media_files = [
                    name for name in docx_zip.namelist()
                    if name.startswith('word/media/') and name.lower().endswith(image_exts)
                ]
                for media_name in media_files:
                    suffix = os.path.splitext(media_name)[1] or '.png'
                    with docx_zip.open(media_name) as img_file:
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                            tmp.write(img_file.read())
                            tmp_path = tmp.name
                    try:
                        ocr_text = DocumentParser._gemini_ocr(tmp_path, api_key=api_key)
                        if ocr_text.strip():
                            image_texts.append(ocr_text.strip())
                    finally:
                        os.unlink(tmp_path)
        except Exception as e:
            print(f"[DocumentParser DOCX image warning] {e}")

        if image_texts:
            image_block = '\n\n'.join(image_texts)
            text = f"{text}\n\n{image_block}".strip() if text else image_block

        return text

    @staticmethod
    def _parse_txt(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
