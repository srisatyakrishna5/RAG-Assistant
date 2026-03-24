from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from config import DOC_INTELLIGENCE_ENDPOINT, DOC_INTELLIGENCE_KEY


def analyze_pdf(pdf_bytes: bytes) -> list[dict]:
    """Analyze a PDF with Azure Document Intelligence and return a list of page dicts.

    Each dict has keys: page_number (int), content (str).
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
