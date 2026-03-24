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
