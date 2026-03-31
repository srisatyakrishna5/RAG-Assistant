"""
services/search_index.py — Azure AI Search index lifecycle and document upload.

This module is responsible for two concerns:

1. **Schema management** — :func:`ensure_search_index` creates the search index
   with the correct field definitions the first time the application is used.
   Subsequent calls are safe (idempotent: the function does nothing if the index
   already exists).

2. **Document ingestion** — :func:`upload_chunks_to_index` takes the list of
   text chunks produced by the chunker, generates vector embeddings for them
   in batches of 16 (to respect OpenAI token limits), and uploads them to the
   index in batches of 100 (to respect Search API request-size limits).

Index schema overview
---------------------
``id``              — Primary key (string, SHA-256 derived)
``document_name``   — Source filename, used as a filter field
``content``         — Full chunk text, full-text searchable
``page_number``     — Source page, used for citations and filtering
``offset``          — Character offset within the page, used for ordering
``content_vector``  — Float32 HNSW vector (3072-dimensional), used for
                       approximate nearest-neighbour (ANN) similarity search
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from config import SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX_NAME
from services.embeddings import generate_embeddings


def ensure_search_index() -> None:
    """Create the Azure AI Search index if it does not already exist.

    Uses the ``SearchIndexClient`` (management plane) to check whether an index
    named ``SEARCH_INDEX_NAME`` is present.  If not, it creates the index with
    the schema required by this application (see module docstring for full field
    list).

    The vector search configuration uses an **HNSW** (Hierarchical Navigable
    Small World) algorithm, which provides sub-linear approximate nearest-
    neighbour search across the stored embedding vectors.  The
    ``content_vector`` field is configured for 3072 dimensions to accommodate
    the ``text-embedding-3-large`` model; the default deployment
    (``text-embedding-ada-002``) produces 1536-dimensional vectors which are
    padded/handled automatically by the SDK.

    This function is called every time a document is uploaded.  It is safe to
    call multiple times — it performs a list-then-create pattern so it never
    overwrites an existing index or its data.

    Raises:
        azure.core.exceptions.HttpResponseError: If the Search service returns
            an error (e.g., invalid credentials or quota exceeded).
    """
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="document_name", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="offset", type=SearchFieldDataType.Int32, filterable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="default-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
        profiles=[
            VectorSearchProfile(
                name="default-profile",
                algorithm_configuration_name="default-hnsw",
            )
        ],
    )

    index = SearchIndex(
        name=SEARCH_INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
    )

    existing = [idx.name for idx in index_client.list_indexes()]
    if SEARCH_INDEX_NAME not in existing:
        index_client.create_index(index)


def upload_chunks_to_index(chunks: list[dict]) -> None:
    """Embed document chunks and upload them to the Azure AI Search index.

    This function handles the full ingestion pipeline after chunking:

    1. **Batch embedding generation** — Extracts the ``content`` string from
       each chunk and calls :func:`~services.embeddings.generate_embeddings`
       in sub-batches of 16 texts at a time.  The batch size of 16 keeps
       individual requests within the Azure OpenAI token-per-request limit.

    2. **Document assembly** — Merges each original chunk dictionary with its
       corresponding embedding vector to form the final document object
       expected by the Search index schema.

    3. **Batched upload** — Sends the assembled documents to Azure AI Search
       in batches of 100 using ``upload_documents``.  Batching is required
       because the Search REST API imposes a maximum payload size per request.
       The ``upload_documents`` action performs an **upsert**: if a document
       with the same ``id`` already exists, it is replaced; otherwise, a new
       document is inserted.

    Args:
        chunks (list[dict]): List of chunk dictionaries as produced by
            :func:`~services.chunker.chunk_pages`.  Each dict must contain:
            - ``id`` (str): Unique chunk identifier (used as the document key).
            - ``content`` (str): Text content to embed and store.
            - ``document_name`` (str): Source document filename.
            - ``page_number`` (int): Source page number.
            - ``offset`` (int): Character offset within the source page.

    Raises:
        openai.RateLimitError: If the embedding API rate limit is exceeded
            during the batched embedding calls.
        azure.core.exceptions.HttpResponseError: If the Search service
            rejects the upload (e.g., schema mismatch or quota exceeded).
    """
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    texts = [c["content"] for c in chunks]

    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), 16):
        all_embeddings.extend(generate_embeddings(texts[i : i + 16]))

    documents = [
        {
            "id": chunk["id"],
            "document_name": chunk.get("document_name", ""),
            "content": chunk["content"],
            "page_number": chunk["page_number"],
            "offset": chunk["offset"],
            "content_vector": embedding,
        }
        for chunk, embedding in zip(chunks, all_embeddings)
    ]

    for i in range(0, len(documents), 100):
        search_client.upload_documents(documents=documents[i : i + 100])
