"""
services/search.py — Hybrid full-text and vector document retrieval.

This module exposes three public functions used by the Streamlit UI:

- :func:`hybrid_search` — The core retrieval function. Called for every user
  question to find the most relevant document chunks.
- :func:`get_indexed_document_names` — Returns the list of documents that have
  been indexed, used to populate the Summary tab dropdown.
- :func:`fetch_chunks_by_document` — Retrieves *all* chunks for one document
  in reading order, used to build the full-document summary.

**Hybrid search explained**

Azure AI Search supports two complementary retrieval strategies that are
combined in a single request:

* **Full-text (BM25)** — Matches documents based on term frequency and inverse
  document frequency.  Fast but purely keyword-based; misses synonyms and
  paraphrases.
* **Vector (ANN/HNSW)** — Matches documents whose embedding vectors are
  closest to the query embedding in semantic space.  Captures meaning even
  when exact keywords differ.

Azure AI Search fuses the two score lists using **Reciprocal Rank Fusion
(RRF)**, which re-ranks results by their combined positions rather than raw
scores, producing a single unified ranking that is typically better than
either strategy alone.
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from config import SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX_NAME
from services.embeddings import generate_embeddings


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve the most relevant document chunks for a user query.

    Performs a **hybrid search** that combines traditional BM25 full-text
    matching with HNSW approximate nearest-neighbour vector similarity.  Both
    strategies run in a single request to Azure AI Search and the results are
    merged using Reciprocal Rank Fusion (RRF) before the top-``k`` are
    returned.

    Steps:
        1. Embed the query string into a float vector using
           :func:`~services.embeddings.generate_embeddings`.
        2. Wrap the vector in a ``VectorizedQuery`` targeting the
           ``content_vector`` field.
        3. Issue a Search request that supplies both ``search_text`` (for
           BM25) and ``vector_queries`` (for ANN).
        4. Map the raw search results to plain dictionaries and return them.

    Args:
        query (str): The user's natural-language question.  This string is
            both embedded (for vector search) and used as-is for full-text
            search.
        top_k (int): Maximum number of results to return.  Passed to both
            the vector query (``k_nearest_neighbors``) and the overall search
            request (``top``).  Defaults to ``5``.

    Returns:
        list[dict]: Up to ``top_k`` result dictionaries ordered from most to
            least relevant.  Each dictionary contains:
            - ``id`` (str): Unique chunk identifier.
            - ``content`` (str): Full text of the matching chunk.
            - ``page_number`` (int): Source page number (used for citations).
            - ``score`` (float): RRF fusion score assigned by Azure AI Search
              (higher is more relevant).

    Raises:
        azure.core.exceptions.HttpResponseError: If the search service is
            unavailable or returns an error response.
        openai.AuthenticationError: If the embedding API key is invalid.

    Example:
        >>> results = hybrid_search("What are the main findings?", top_k=3)
        >>> results[0]['page_number']
        4
        >>> results[0]['score']
        0.0324
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
    """Return a sorted list of distinct document names present in the search index.

    Issues a wildcard search (``*``) retrieving only the ``document_name``
    field to enumerate every document that has been ingested.  Duplicates (one
    entry per chunk) are de-duplicated using a set comprehension before
    sorting.

    The function fetches up to 1000 results.  For production use-cases with a
    very large number of documents, this should be replaced with a proper
    facet query.

    Returns:
        list[str]: Alphabetically sorted list of document names (filenames).
            Returns an empty list if no documents have been indexed yet.

    Raises:
        azure.core.exceptions.HttpResponseError: If the search service is
            unavailable or returns an error response.
    """
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
    """Retrieve all indexed chunks for a specific document in reading order.

    Issues a wildcard search with an OData filter on ``document_name`` to
    collect every chunk that belongs to the requested document.  The results
    are then sorted client-side by ``(page_number, offset)`` to reconstruct
    reading order, which may differ from the order returned by the search API.

    This function is used exclusively by the **Summary** tab to assemble the
    full document text before passing it to
    :func:`~services.llm.generate_document_summary`.

    Args:
        document_name (str): Exact filename as stored in the index
            (e.g., ``"annual_report_2024.pdf"``).  The filter is case-sensitive
            and must match the value stored during indexing.

    Returns:
        list[dict]: All chunk dictionaries for the document, sorted by
            ``page_number`` ascending then ``offset`` ascending.  Each dict
            contains:
            - ``id`` (str): Unique chunk identifier.
            - ``content`` (str): Text content of the chunk.
            - ``page_number`` (int): Source page number.
            - ``offset`` (int): Character offset within the source page.
            Returns an empty list if no matching chunks are found.

    Raises:
        azure.core.exceptions.HttpResponseError: If the search service is
            unavailable or returns an error response.
    """
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
