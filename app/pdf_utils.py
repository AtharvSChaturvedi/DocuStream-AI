"""
PDF -> page-attributed text chunks.

Keeping page numbers attached to every chunk is what lets the app cite
"page 4 of Smith et al." instead of a vague "somewhere in this paper."
"""
import io
from pypdf import PdfReader


def extract_pages(file_bytes):
    """Returns a list of (page_number, page_text) tuples, 1-indexed."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append((i + 1, text))
    return pages


def chunk_pages(pages, chunk_size=900, overlap=150):
    """Splits each page's text into overlapping character chunks.
    Returns a list of {"text": ..., "page": ...} dicts.

    Character-based chunking is a deliberate simplicity choice for the
    MVP - it's predictable and has no extra dependencies. Swap in a
    token-aware or sentence-aware splitter later if retrieval quality
    needs tightening.
    """
    chunks = []
    for page_num, text in pages:
        text = text.strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "page": page_num})
            if end >= len(text):
                break
            start = end - overlap
    return chunks
