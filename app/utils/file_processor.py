"""
app/utils/file_processor.py
Extracts clean text from uploaded PDF and TXT files.
"""
import os
import re

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


def extract_text_from_file(file_path: str, file_type: str) -> tuple[str, int, int]:
    """
    Extract text from a PDF or TXT file.

    Returns:
        (text, page_count, word_count)
    """
    if file_type == 'pdf':
        return _extract_pdf(file_path)
    elif file_type == 'txt':
        return _extract_txt(file_path)
    else:
        return '', 0, 0


def _extract_pdf(file_path: str) -> tuple[str, int, int]:
    if not PYPDF2_AVAILABLE:
        return '', 0, 0
    try:
        text_parts = []
        page_count = 0
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page_count = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text() or ''
                text_parts.append(page_text)
        text = '\n\n'.join(text_parts)
        text = _clean_text(text)
        word_count = len(text.split())
        return text, page_count, word_count
    except Exception as e:
        print(f'PDF extraction error: {e}')
        return '', 0, 0


def _extract_txt(file_path: str) -> tuple[str, int, int]:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        text = _clean_text(text)
        word_count = len(text.split())
        # Approximate page count (250 words per page)
        page_count = max(1, word_count // 250)
        return text, page_count, word_count
    except Exception as e:
        print(f'TXT extraction error: {e}')
        return '', 0, 0


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and non-printable characters."""
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove non-printable characters (except newlines and tabs)
    text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r' {3,}', '  ', text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks for RAG processing.
    Splits on paragraph/sentence boundaries where possible.
    """
    if not text:
        return []

    # Split into paragraphs first
    paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]

    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > chunk_size and current_chunk:
            chunk_text_str = '\n\n'.join(current_chunk)
            chunks.append(chunk_text_str)
            # Keep last portion for overlap
            overlap_text = chunk_text_str[-overlap:] if len(chunk_text_str) > overlap else chunk_text_str
            current_chunk = [overlap_text]
            current_len = len(overlap_text)

        current_chunk.append(para)
        current_len += para_len + 2  # +2 for '\n\n'

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks
