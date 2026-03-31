from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from config import (
    AZURE_TRANSLATOR_KEY,
    AZURE_TRANSLATOR_REGION,
    LANGUAGE_CONFIG,
)


def _get_client() -> TextTranslationClient:
    """Build a TextTranslationClient using the global endpoint."""
    credential = AzureKeyCredential(AZURE_TRANSLATOR_KEY)
    return TextTranslationClient(credential=credential, region=AZURE_TRANSLATOR_REGION)


def translate_text(text: str, language: str) -> str:
    """Translate text to the target language using the Azure Translator SDK.

    Returns the original text unchanged if:
    - the target language is English, or
    - AZURE_TRANSLATOR_KEY is not configured.
    """
    target_code = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])["translator_code"]
    if target_code == "en" or not AZURE_TRANSLATOR_KEY:
        return text

    client = _get_client()
    response = client.translate(body=[text], to_language=[target_code], from_language="en")
    return response[0].translations[0].text
