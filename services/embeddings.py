"""
services/embeddings.py — Dense vector embedding generation via Azure OpenAI.

Embeddings are high-dimensional floating-point vectors that encode the semantic
meaning of a piece of text.  Two texts that are semantically similar will have
vectors that are close together in this high-dimensional space (measured by
cosine similarity or dot product).  These embeddings power the vector-search
half of the hybrid retrieval used by this application.

Model: ``text-embedding-ada-002`` by default (1536 or 3072 dimensions depending
on the deployment).  The model name is controlled by the
``AZURE_OPENAI_EMBEDDING_DEPLOYMENT`` environment variable.
"""

from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Convert a batch of text strings into dense semantic embedding vectors.

    Creates an ``AzureOpenAI`` client and calls the Embeddings API to convert
    every string in ``texts`` into a fixed-dimension floating-point vector.
    The order of the returned vectors matches the order of the input strings,
    so the caller can safely ``zip(texts, vectors)``.

    The function is intentionally stateless (no caching) — the caller in
    :mod:`services.search_index` is responsible for batching (groups of 16)
    to avoid exceeding the API's per-request token limit.

    Args:
        texts (list[str]): One or more text strings to embed.  Each string
            should be a self-contained piece of text (e.g., a document chunk
            or a user query).  Empty strings are technically valid but will
            produce a zero-like vector.

    Returns:
        list[list[float]]: A list of embedding vectors, one per input text.
            Each vector is a list of floats with a fixed dimensionality
            determined by the deployed embedding model (e.g., 3072 for
            ``text-embedding-3-large``, 1536 for ``text-embedding-ada-002``).

    Raises:
        openai.AuthenticationError: If the API key is invalid or expired.
        openai.RateLimitError: If the Azure OpenAI quota/rate limit is hit.
        openai.BadRequestError: If an input string is too long for the model.

    Example:
        >>> vectors = generate_embeddings(["Hello world", "Goodbye world"])
        >>> len(vectors)          # one vector per input
        2
        >>> len(vectors[0])       # dimensionality of the embedding model
        1536
    """
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    response = client.embeddings.create(
        input=texts,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )
    return [item.embedding for item in response.data]
