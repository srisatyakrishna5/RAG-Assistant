"""
services/llm.py — GPT-4.1 powered answer generation and text summarization.

This module contains the three LLM-facing functions used by the application:

- :func:`generate_answer` — The primary RAG answer function.  Takes a user
  question and retrieved context chunks, calls GPT-4.1, and returns a cited
  answer.
- :func:`summarize_for_speech` — Converts a written answer into a short,
  natural spoken paragraph suitable for text-to-speech synthesis.
- :func:`generate_document_summary` — Generates a comprehensive summary of
  an entire document from all its indexed chunks.

All three functions produce output in English first, then delegate to
:func:`~services.translation.translate_text` to translate into the user's
selected language — this two-step approach keeps the LLM prompts in English
(highest quality) while still supporting multilingual output.
"""

from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
)
from services.translation import translate_text


def _get_client() -> AzureOpenAI:
    """Create and return an authenticated AzureOpenAI client.

    Constructs a new ``AzureOpenAI`` client using the endpoint, API key, and
    API version defined in :mod:`config`.  A new client is created on every
    call — this is intentional as the ``openai`` SDK clients are lightweight
    and stateless, and caching them at module level would complicate testing.

    Returns:
        AzureOpenAI: A configured client ready to make chat completion and
            embedding requests against the Azure OpenAI resource.
    """
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def generate_answer(
    query: str, context_chunks: list[dict], language: str = "English"
) -> str:
    """Generate a grounded, cited answer to a user question from document chunks.

    Constructs a structured prompt that presents the retrieved document chunks
    as numbered context blocks (``[Source N - Page P]``) and instructs GPT-4.1
    to answer the question using only those sources.  The model is directed to
    cite sources explicitly so users can verify which pages support each claim.

    After the English answer is returned by the model, it is passed to
    :func:`~services.translation.translate_text` to convert it to the user's
    selected output language.

    Args:
        query (str): The user's natural-language question as entered in the
            chat interface or transcribed from voice input.
        context_chunks (list[dict]): Ranked list of document chunks returned
            by :func:`~services.search.hybrid_search`.  Each dict must contain
            ``content`` (str) and ``page_number`` (int).
        language (str): Target output language display name as defined in
            ``LANGUAGE_CONFIG`` (e.g., ``"English"``, ``"Hindi"``,
            ``"French"``, ``"Telugu"``).  Defaults to ``"English"``,
            in which case no translation is performed.

    Returns:
        str: A comprehensive answer in the target language with inline
            citations referencing ``[Source N - Page P]`` markers.
            If the model cannot find a relevant answer in the context, it
            returns a polite "not found" message.

    Raises:
        openai.AuthenticationError: If the API key is invalid.
        openai.RateLimitError: If the GPT deployment quota is exceeded.
        openai.BadRequestError: If the combined context + question exceeds
            the model's context window.
    """
    client = _get_client()

    context_parts = [
        f"[Source {i} - Page {chunk['page_number']}]\n{chunk['content']}"
        for i, chunk in enumerate(context_chunks, 1)
    ]
    context_text = "\n\n---\n\n".join(context_parts)

    system_prompt = (
        "You are a helpful assistant that answers questions based on provided document excerpts. "
        "Always cite your sources using the [Source N - Page P] references provided. "
        "If the answer is not found in the provided context, say so clearly. "
        "Always respond in English."
    )
    user_prompt = (
        f"Context from the document:\n\n{context_text}\n\n---\n\n"
        f"Question: {query}\n\n"
        "Provide a comprehensive answer with citations referencing the source numbers and page numbers above."
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1500,
    )

    english_answer = response.choices[0].message.content
    return translate_text(english_answer, language)


def summarize_for_speech(answer: str, language: str = "English") -> str:
    """Convert a written answer into a short, natural spoken paragraph.

    Written document answers often contain markdown formatting (bullet points,
    citation markers like ``[Source 1]``, bold text, etc.) that sounds awkward
    when read aloud by a TTS engine.  This function uses GPT-4.1 to rewrite
    the answer as a single, polished spoken paragraph of 2–4 sentences with
    all formatting removed.

    The system prompt enforces strict rules:

    * Exactly **one paragraph** of 2–4 flowing sentences.
    * **No lists**, bullet points, dashes, colons at line start, or citation
      markers (``[Source N]``).
    * **No abbreviations** without spelling them out.
    * Sentences are connected with transitional words for natural flow.
    * Does **not** start with filler phrases like "Sure", "Here is", or
      "In summary".

    The condensed English paragraph is then translated to the target language
    by :func:`~services.translation.translate_text`.

    Args:
        answer (str): The full written answer produced by :func:`generate_answer`
            (may contain markdown, citations, and lists).
        language (str): Target output language display name.  Defaults to
            ``"English"`` (no translation performed).

    Returns:
        str: A single spoken paragraph in the target language, optimised for
            natural text-to-speech delivery.

    Raises:
        openai.AuthenticationError: If the API key is invalid.
        openai.RateLimitError: If the GPT deployment quota is exceeded.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You convert a written answer into a short script for a voice assistant "
                    "to read aloud. Rules:\n"
                    "- Write exactly ONE paragraph with 2-4 flowing sentences.\n"
                    "- Use simple, natural spoken English - as if explaining to a friend.\n"
                    "- NEVER use bullet points, numbered lists, citation markers like "
                    "[Source 1], asterisks, dashes, colons at the start of a line, or any formatting.\n"
                    "- NEVER use abbreviations or acronyms without spelling them out.\n"
                    "- Connect sentences with transitional words so the paragraph reads as one continuous thought.\n"
                    "- Do NOT start with phrases like 'Sure', 'Here is', or 'In summary'."
                ),
            },
            {
                "role": "user",
                "content": f"Convert this answer into a spoken paragraph:\n\n{answer}",
            },
        ],
        temperature=0.4,
        max_tokens=300,
    )

    english_summary = response.choices[0].message.content.strip()
    return translate_text(english_summary, language)


def generate_document_summary(
    chunks: list[dict], language: str = "English"
) -> str:
    """Generate a comprehensive summary of an entire document from its indexed chunks.

    Concatenates all chunk content in page order (as provided) into a single
    context block and requests a structured, well-organised summary from
    GPT-4.1.  Unlike :func:`generate_answer` (which answers a specific
    question), this function instructs the model to capture the overall
    document: key topics, findings, arguments, and conclusions.

    The system prompt requests:

    * A **well-structured** summary with bullet points where appropriate.
    * **Page-level citations** when referencing specific details.
    * Response directly in the target language.

    The summary uses ``max_tokens=3000`` (compared to 1500 for
    :func:`generate_answer`) because whole-document summaries are inherently
    longer.

    Args:
        chunks (list[dict]): All chunks for a single document, as returned by
            :func:`~services.search.fetch_chunks_by_document`.  Each dict must
            contain ``content`` (str) and ``page_number`` (int).  Chunks should
            be ordered by page then offset.
        language (str): Target output language display name.  Defaults to
            ``"English"``.

    Returns:
        str: A formatted multi-paragraph (or bulleted) summary of the
            document in the target language, with page-level citations.

    Raises:
        openai.AuthenticationError: If the API key is invalid.
        openai.RateLimitError: If the GPT deployment quota is exceeded.
        openai.BadRequestError: If the total document text exceeds the model's
            context window (very large documents may need to be split further).
    """
    client = _get_client()

    context_parts = [
        f"[Page {chunk['page_number']}]\n{chunk['content']}"
        for chunk in chunks
    ]
    context_text = "\n\n---\n\n".join(context_parts)

    system_prompt = (
        "You are a helpful assistant that produces comprehensive document summaries. "
        "You will receive the full text of a document split into page-level chunks. "
        "Write a well-structured summary that captures the key topics, findings, "
        "arguments, and conclusions of the document. Use bullet points where appropriate. "
        "Reference page numbers when citing specific details. "
        f"Always respond in {language}."
    )
    user_prompt = (
        f"Document content:\n\n{context_text}\n\n---\n\n"
        "Provide a comprehensive summary of this entire document."
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=3000,
    )

    english_summary = response.choices[0].message.content
    return translate_text(english_summary, language)


def generate_podcast_script(chunks: list[dict], language: str = "English") -> list[dict]:
    """Generate a podcast-style script from document chunks.

    Converts document chunks into a list of spoken segments suitable for
    text-to-speech synthesis.  Each segment is a natural, conversational
    paragraph that a single speaker would read aloud — free of markdown,
    citation markers, and other written-text artifacts.

    The LLM is prompted to produce a JSON array of segment objects, each
    with a ``text`` field containing 2–4 flowing sentences.  The segments
    are ordered to follow the document's logical structure and connected
    with transitions so the podcast feels cohesive.

    Args:
        chunks (list[dict]): All chunks for a single document, ordered by
            page then offset (as returned by
            :func:`~services.search.fetch_chunks_by_document`).
        language (str): Target language display name.  Defaults to
            ``"English"``.

    Returns:
        list[dict]: Ordered list of segment dicts, each containing:
            - ``segment`` (int): 1-based segment number.
            - ``text`` (str): Spoken paragraph for this segment.
    """
    import json as _json

    client = _get_client()

    context_parts = [
        f"[Page {chunk['page_number']}]\n{chunk['content']}"
        for chunk in chunks
    ]
    context_text = "\n\n---\n\n".join(context_parts)

    system_prompt = (
        "You are a professional podcast scriptwriter. Convert the provided document "
        "into a compelling podcast script that a single host would read aloud.\n\n"
        "Rules:\n"
        "- Produce between 4 and 15 segments depending on document length.\n"
        "- Each segment should be 2-5 sentences of natural, conversational speech.\n"
        "- Start with a brief welcoming introduction that names the document topic.\n"
        "- End with a short closing/wrap-up segment.\n"
        "- Use transitions between segments so the podcast flows naturally.\n"
        "- NEVER use bullet points, numbered lists, citation markers, asterisks, "
        "or any markdown formatting.\n"
        "- NEVER use abbreviations without spelling them out.\n"
        "- Write as spoken English — contractions and conversational tone are encouraged.\n"
        "- Return ONLY a JSON array of objects with keys 'segment' (int, 1-based) "
        "and 'text' (string). No other text or explanation.\n"
        f"- Write the script in {language}."
    )
    user_prompt = (
        f"Document content:\n\n{context_text}\n\n---\n\n"
        "Convert the above document into a podcast script. Return valid JSON only."
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    segments = _json.loads(raw)
    if isinstance(segments, list):
        return segments

    raise ValueError("LLM did not return a valid JSON array for the podcast script.")
