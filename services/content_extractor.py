"""
Content Extractor Module
Extracts plain text from supported file formats: PDF, TXT, CSV, IPYNB, DOCX.
Dispatches by file extension; raises ValueError for unsupported types or size violations.
"""

import csv
import io
import json
import logging
import os

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv", ".ipynb", ".docx"}


def extract_text(file_bytes: bytes, filename: str, max_size_mb: float = 50.0) -> str:
    """
    Extract plain text from a file. Dispatches by file extension.

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used to determine format).
        max_size_mb: Size limit in megabytes (default 50 MB).

    Returns:
        Extracted text as a string.

    Raises:
        ValueError: Unsupported extension, size limit exceeded, or parse error.
    """
    if len(file_bytes) > max_size_mb * 1024 * 1024:
        raise ValueError(f"File exceeds {max_size_mb}MB limit")

    _, ext = os.path.splitext(filename.lower())

    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Supported formats: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif ext == ".txt":
        return _extract_txt(file_bytes)
    elif ext == ".csv":
        return _extract_csv(file_bytes)
    elif ext == ".ipynb":
        return _extract_ipynb(file_bytes)
    elif ext == ".docx":
        return _extract_docx(file_bytes)

    return ""


def _extract_pdf(file_bytes: bytes) -> str:
    result = extract_text_from_pdf_bytes(file_bytes)
    return result if result is not None else ""


def _extract_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def _extract_csv(file_bytes: bytes) -> str:
    text = file_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    return "\n".join(", ".join(row) for row in reader)


def _extract_ipynb(file_bytes: bytes) -> str:
    try:
        notebook = json.loads(file_bytes.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid .ipynb file: {exc}") from exc

    parts = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") not in ("code", "markdown"):
            continue
        source = cell.get("source", [])
        cell_text = "".join(source) if isinstance(source, list) else str(source)
        if cell_text.strip():
            parts.append(cell_text)
    return "\n---\n".join(parts)


def _extract_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise ValueError("DOCX support requires python-docx package")

    doc = Document(io.BytesIO(file_bytes))
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# PDF extraction (merged from pdf_processor.py)
# ---------------------------------------------------------------------------

def extract_text_from_pdf_bytes(pdf_bytes):
    """
    Extract text content from PDF binary data

    Args:
        pdf_bytes (bytes): PDF file content as bytes

    Returns:
        str: Extracted text from all pages, or None if extraction fails
    """
    try:
        import PyPDF2
        from io import BytesIO

        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text_content = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text:
                text_content.append(text)

        full_text = "\n\n".join(text_content)

        if not full_text.strip():
            print("Warning: PDF appears to be empty or contains only images")
            return None

        return full_text

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_text_from_pdf_file(pdf_path):
    """
    Extract text content from PDF file path

    Args:
        pdf_path (str): Path to PDF file

    Returns:
        str: Extracted text from all pages, or None if extraction fails
    """
    try:
        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()
        return extract_text_from_pdf_bytes(pdf_bytes)
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None
