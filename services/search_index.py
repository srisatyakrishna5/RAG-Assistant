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
    """Create the AI Search index if it does not already exist."""
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
    """Embed and upload document chunks to the AI Search index in batches."""
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
