"""
services/chunker.py — Overlapping character-level text chunking.

Long documents must be broken into smaller pieces ("chunks") before they can
be embedded and stored in a vector index.  This module implements a sliding-
window chunking strategy with configurable overlap so that context at chunk
boundaries is never lost.

Why overlap?
    If a meaningful sentence happens to straddle the boundary between two
    consecutive windows, a zero-overlap strategy would split that sentence
    across two chunks and weaken retrieval for queries that match that sentence.
    The default 200-character overlap ensures boundary content appears in at
    least two chunks, increasing the chance of a relevant match.
"""

import hashlib


def chunk_pages(
    pages: list[dict],
    document_name: str = "",
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[dict]:
    """Split per-page text into overlapping fixed-size character windows.

    Iterates over every page returned by ``analyze_pdf`` and applies a
    sliding window of ``chunk_size`` characters, advancing by
    ``chunk_size - overlap`` characters at each step.  Pages that contain
    only whitespace are skipped entirely.

    Each resulting chunk is assigned a deterministic identifier derived from
    the document name, the page number, and the character offset, so that
    re-indexing the same document produces the same IDs (enabling upsert
    semantics in Azure AI Search).

    Args:
        pages (list[dict]): Ordered list of page dictionaries as returned by
            :func:`~services.document_intelligence.analyze_pdf`.  Each dict
            must contain ``page_number`` (int) and ``content`` (str).
        document_name (str): Human-readable name of the source document
            (usually the uploaded filename).  Stored in every chunk so the
            search index can filter by document.  Defaults to an empty string.
        chunk_size (int): Maximum number of characters per chunk.  The last
            chunk on a page may be shorter.  Defaults to ``1000``.
        overlap (int): Number of characters shared between consecutive chunks
            on the same page.  Must be strictly less than ``chunk_size``.
            Defaults to ``200``.

    Returns:
        list[dict]: Flat list of chunk dictionaries across all pages.  Each
            dictionary contains:
            - ``id`` (str): First 16 hex characters of the SHA-256 hash of
              ``"{document_name}-{page_number}-{offset}"``.
            - ``document_name`` (str): Name of the source document.
            - ``content`` (str): The text slice for this chunk.
            - ``page_number`` (int): 1-based page number of the source page.
            - ``offset`` (int): Character offset within the page where this
              chunk starts.

    Example:
        >>> pages = [{'page_number': 1, 'content': 'A' * 2500}]
        >>> chunks = chunk_pages(pages, document_name='test.pdf')
        >>> len(chunks)   # ceil((2500 - 200) / 800) + 1 = 4
        4
        >>> chunks[0]['offset'], chunks[1]['offset']
        (0, 800)
    """
    chunks = []
    for page in pages:
        text = page["content"]
        page_num = page["page_number"]
        if not text.strip():
            continue

        start = 0
        while start < len(text):
            chunk_text = text[start : start + chunk_size]
            chunk_id = hashlib.sha256(
                f"{document_name}-{page_num}-{start}".encode()
            ).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "document_name": document_name,
                    "content": chunk_text,
                    "page_number": page_num,
                    "offset": start,
                }
            )
            start += chunk_size - overlap
    return chunks
