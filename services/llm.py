from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
)
from services.translation import translate_text


def _get_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def generate_answer(
    query: str, context_chunks: list[dict], language: str = "English"
) -> str:
    """Generate a grounded answer in English via GPT-4.1, then translate to target language.

    Uses retrieved document chunks as context and cites sources.
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
    """Condense the answer into a natural spoken paragraph in English, then translate.

    The result is intended to be passed directly to TTS synthesis.
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
