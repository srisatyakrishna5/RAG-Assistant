"""
services/translation.py — On-demand text translation via Azure Translator.

This module provides a single public function, :func:`translate_text`, which
converts English text into the user's selected output language.  It is called
as the final step of both :func:`~services.llm.generate_answer` and
:func:`~services.llm.summarize_for_speech`, meaning that the LLM always
generates output in English (highest quality) and translation is applied
after the fact.

**Graceful degradation** — If ``AZURE_TRANSLATOR_KEY`` is not configured, the
function returns the original English text unchanged.  Likewise, if the
target language *is* English, no API call is made.  This means the app
remains fully functional for English users without requiring an Azure
Translator resource.
"""

from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from config import (
    AZURE_TRANSLATOR_KEY,
    AZURE_TRANSLATOR_REGION,
    LANGUAGE_CONFIG,
)


def _get_client() -> TextTranslationClient:
    """Build an authenticated ``TextTranslationClient`` instance.

    Creates and returns a ``TextTranslationClient`` using the global
    ``AZURE_TRANSLATOR_KEY`` and ``AZURE_TRANSLATOR_REGION`` values from
    :mod:`config`.  The client connects to the global Azure Translator
    endpoint (``api.cognitive.microsofttranslator.com``).

    This helper is called lazily from :func:`translate_text` so the client
    is only created when a translation is actually needed (i.e., when the
    target language is not English and a key is configured).

    Returns:
        TextTranslationClient: Authenticated client ready to call the
            Translator REST API.
    """
    credential = AzureKeyCredential(AZURE_TRANSLATOR_KEY)
    return TextTranslationClient(credential=credential, region=AZURE_TRANSLATOR_REGION)


def translate_text(text: str, language: str) -> str:
    """Translate English text to the target language using Azure Translator.

    Looks up the ISO 639-1 language code for the requested language from
    ``LANGUAGE_CONFIG``, then calls the Azure Translator REST API to translate
    the input text.  The source language is always assumed to be English
    (``"en"``) because all LLM outputs are generated in English before
    translation.

    The function short-circuits (returns ``text`` unchanged) in two cases:

    1. The target language is **English** — no translation needed.
    2. ``AZURE_TRANSLATOR_KEY`` is **not set** — the service is not
       configured; the app continues to work with English output.

    Args:
        text (str): The English text to translate.  May be a complete answer
            with multiple paragraphs or a short spoken paragraph.
        language (str): Target language display name as defined in
            ``LANGUAGE_CONFIG``.  If the name is not found in the config,
            falls back to ``"English"`` (no translation).

    Returns:
        str: Translated text in the target language.  If the target is
            English or no key is configured, the original ``text`` is
            returned unchanged.

    Raises:
        azure.core.exceptions.HttpResponseError: If the Translator service
            returns an HTTP error (e.g., unsupported language pair, quota
            exceeded, or invalid API key).

    Example:
        >>> translate_text("Hello, how are you?", "French")
        'Bonjour, comment allez-vous ?'
        >>> translate_text("Hello", "English")  # no-op
        'Hello'
    """
    target_code = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])["translator_code"]
    if target_code == "en" or not AZURE_TRANSLATOR_KEY:
        return text

    client = _get_client()
    response = client.translate(body=[text], to_language=[target_code], from_language="en")
    return response[0].translations[0].text
