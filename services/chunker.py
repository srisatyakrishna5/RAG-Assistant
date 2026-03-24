import hashlib


def chunk_pages(
    pages: list[dict], chunk_size: int = 1000, overlap: int = 200
) -> list[dict]:
    """Split page content into overlapping text chunks with source metadata.

    Each chunk dict has keys: id, content, page_number, offset.
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
            chunk_id = hashlib.sha256(f"{page_num}-{start}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk_text,
                    "page_number": page_num,
                    "offset": start,
                }
            )
            start += chunk_size - overlap
    return chunks
