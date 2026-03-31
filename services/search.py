from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from config import SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX_NAME
from services.embeddings import generate_embeddings


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Perform hybrid (text + vector) search and return ranked result dicts.

    Each result dict has keys: id, content, page_number, score.
    """
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    query_embedding = generate_embeddings([query])[0]

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k,
        fields="content_vector",
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=top_k,
        select=["id", "content", "page_number"],
    )

    return [
        {
            "id": r["id"],
            "content": r["content"],
            "page_number": r["page_number"],
            "score": r["@search.score"],
        }
        for r in results
    ]


def get_indexed_document_names() -> list[str]:
    """Return a sorted list of distinct document names in the search index."""
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    results = search_client.search(
        search_text="*",
        select=["document_name"],
        top=1000,
    )

    names = {r["document_name"] for r in results if r.get("document_name")}
    return sorted(names)


def fetch_chunks_by_document(document_name: str) -> list[dict]:
    """Retrieve all chunks for a specific document, ordered by page and offset."""
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    results = search_client.search(
        search_text="*",
        filter=f"document_name eq '{document_name}'",
        select=["id", "content", "page_number", "offset"],
        top=1000,
    )

    chunks = [
        {
            "id": r["id"],
            "content": r["content"],
            "page_number": r["page_number"],
            "offset": r.get("offset", 0),
        }
        for r in results
    ]
    chunks.sort(key=lambda c: (c["page_number"], c["offset"]))
    return chunks
