import os
from dotenv import load_dotenv

load_dotenv()

# --------------- Azure Document Intelligence ---------------
DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")

# --------------- Azure AI Search ---------------
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "rag-documents")

# --------------- Azure OpenAI ---------------
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
)
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

# --------------- Azure Speech ---------------
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "")

# --------------- Azure Translator ---------------
AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY", "")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "")

# --------------- Language Configuration ---------------
# Maps display name -> ISO 639-1 translator code, Azure Neural voice, speech locale.
LANGUAGE_CONFIG = {
    "English": {
        "translator_code": "en",
        "voice": "en-US-JennyNeural",
        "speech_locale": "en-US",
    },
    "Hindi": {
        "translator_code": "hi",
        "voice": "hi-IN-SwaraNeural",
        "speech_locale": "hi-IN",
    },
    "French": {
        "translator_code": "fr",
        "voice": "fr-FR-DeniseNeural",
        "speech_locale": "fr-FR",
    },
}
