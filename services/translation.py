import requests

from config import (
    AZURE_TRANSLATOR_KEY,
    AZURE_TRANSLATOR_REGION,
    TRANSLATOR_ENDPOINT,
    LANGUAGE_CONFIG,
)


def translate_text(text: str, language: str) -> str:
    """Translate text to the target language using Azure Translator.

    Returns the original text unchanged if:
    - the target language is English, or
    - AZURE_TRANSLATOR_KEY is not configured.
    """
    target_code = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])["translator_code"]
    if target_code == "en" or not AZURE_TRANSLATOR_KEY:
        return text

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
    }
    params = {"api-version": "3.0", "from": "en", "to": target_code}

    resp = requests.post(
        TRANSLATOR_ENDPOINT,
        params=params,
        headers=headers,
        json=[{"text": text}],
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()[0]["translations"][0]["text"]
