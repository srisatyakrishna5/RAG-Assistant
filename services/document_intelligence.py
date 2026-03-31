"""
services/document_intelligence.py — PDF text extraction via Azure Document Intelligence.

This module wraps the Azure AI Document Intelligence "prebuilt-layout" model,
which understands complex PDF layouts (tables, columns, headers, etc.) and
returns the textual content organised per page.  The extracted pages are the
starting point of the entire RAG ingestion pipeline.
"""

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from config import DOC_INTELLIGENCE_ENDPOINT, DOC_INTELLIGENCE_KEY


def analyze_pdf(pdf_bytes: bytes) -> list[dict]:
    """Extract structured text from a PDF file using Azure Document Intelligence.

    Sends the raw PDF bytes to the Azure Document Intelligence service using the
    ``prebuilt-layout`` model, which is designed to handle a wide variety of
    document formats including scanned images, multi-column layouts, and tables.
    The service performs OCR if necessary and returns the text content organized
    per page.

    Args:
        pdf_bytes (bytes): The raw binary content of a PDF file, typically
            obtained by reading an uploaded file with ``file.read()``.

    Returns:
        list[dict]: A list of page dictionaries, one entry per page in the PDF.
            Each dictionary contains:
            - ``page_number`` (int): 1-based page index as returned by the service.
            - ``content`` (str): Full text content of the page with each line
              separated by a newline character (``\\n``).

    Raises:
        azure.core.exceptions.HttpResponseError: If the Document Intelligence
            service returns an HTTP error (e.g., invalid credentials, quota
            exceeded, or malformed request).
        azure.core.exceptions.ServiceRequestError: If the service endpoint is
            unreachable due to network issues.

    Example:
        >>> with open("report.pdf", "rb") as f:
        ...     pages = analyze_pdf(f.read())
        >>> pages[0]
        {'page_number': 1, 'content': 'Executive Summary\\nThis report covers...'}
    """
    client = DocumentIntelligenceClient(
        endpoint=DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(DOC_INTELLIGENCE_KEY),
    )

    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
    )
    result = poller.result()

    pages = []
    for page in result.pages:
        lines_text = [line.content for line in page.lines] if page.lines else []
        pages.append(
            {
                "page_number": page.page_number,
                "content": "\n".join(lines_text),
            }
        )
    return pages
