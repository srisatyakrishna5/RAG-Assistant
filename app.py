import os
import io
import tempfile
import hashlib
import streamlit as st
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchableField,
)
from openai import AzureOpenAI

try:
    import azure.cognitiveservices.speech as speechsdk
    SPEECH_SDK_AVAILABLE = True
except ImportError:
    SPEECH_SDK_AVAILABLE = False

load_dotenv()

# --------------- Configuration ---------------
DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "rag-documents")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
)
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "")

AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY", "")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "")
# Global Azure Translator endpoint (no custom domain needed)
_TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"

# --------------- Language Configuration ---------------
# Maps display name → ISO 639-1 code for Azure Translator, Azure Neural voice, speech locale.
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


# --------------- Helpers ---------------
def get_doc_intelligence_client() -> DocumentIntelligenceClient:
    return DocumentIntelligenceClient(
        endpoint=DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(DOC_INTELLIGENCE_KEY),
    )


def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def get_search_index_client() -> SearchIndexClient:
    return SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_KEY),
    )


def get_search_client() -> SearchClient:
    return SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )


# --------------- Document Intelligence ---------------
def analyze_pdf(pdf_bytes: bytes) -> list[dict]:
    """Analyze a PDF with Azure Document Intelligence and return pages with content."""
    client = get_doc_intelligence_client()

    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
    )
    result = poller.result()

    pages = []
    for page in result.pages:
        lines_text = []
        if page.lines:
            for line in page.lines:
                lines_text.append(line.content)
        pages.append(
            {
                "page_number": page.page_number,
                "content": "\n".join(lines_text),
            }
        )
    return pages


# --------------- Chunking ---------------
def chunk_pages(pages: list[dict], chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    """Split page content into overlapping text chunks with source metadata."""
    chunks = []
    for page in pages:
        text = page["content"]
        page_num = page["page_number"]
        if not text.strip():
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunk_id = hashlib.sha256(
                f"{page_num}-{start}".encode()
            ).hexdigest()[:16]
            chunks.append(
                {
                    "id": chunk_id,
                    "content": chunk_text,
                    "page_number": page_num,
                    "offset": start,
                }
            )
            start += chunk_size - overlap
    return chunks


# --------------- Embeddings ---------------
def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using Azure OpenAI."""
    client = get_openai_client()
    response = client.embeddings.create(
        input=texts,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )
    return [item.embedding for item in response.data]


# --------------- AI Search Index ---------------
def ensure_search_index():
    """Create the search index if it doesn't already exist."""
    index_client = get_search_index_client()

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(
            name="page_number", type=SearchFieldDataType.Int32, filterable=True
        ),
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

    existing_names = [idx.name for idx in index_client.list_indexes()]
    if SEARCH_INDEX_NAME not in existing_names:
        index_client.create_index(index)


def upload_chunks_to_index(chunks: list[dict]):
    """Upload document chunks (with embeddings) to the search index."""
    search_client = get_search_client()

    texts = [c["content"] for c in chunks]

    # Batch embeddings in groups of 16
    all_embeddings: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_embeddings.extend(generate_embeddings(batch))

    documents = []
    for chunk, embedding in zip(chunks, all_embeddings):
        documents.append(
            {
                "id": chunk["id"],
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "offset": chunk["offset"],
                "content_vector": embedding,
            }
        )

    # Upload in batches of 100
    for i in range(0, len(documents), 100):
        batch = documents[i : i + 100]
        search_client.upload_documents(documents=batch)


# --------------- Search & RAG ---------------
def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Perform hybrid (text + vector) search against the index."""
    from azure.search.documents.models import VectorizedQuery

    search_client = get_search_client()
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

    hits = []
    for r in results:
        hits.append(
            {
                "id": r["id"],
                "content": r["content"],
                "page_number": r["page_number"],
                "score": r["@search.score"],
            }
        )
    return hits


# --------------- Translation ---------------
def translate_text(text: str, language: str) -> str:
    """Translate text to the target language using Azure Translator.

    If the language is English or the Translator service is not configured,
    the original text is returned unchanged.
    """
    import requests as _requests

    target_code = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])["translator_code"]
    if target_code == "en" or not AZURE_TRANSLATOR_KEY:
        return text  # no translation needed / service not configured

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
    }
    params = {"api-version": "3.0", "from": "en", "to": target_code}
    body = [{"text": text}]

    resp = _requests.post(
        _TRANSLATOR_ENDPOINT, params=params, headers=headers, json=body, timeout=30
    )
    resp.raise_for_status()
    return resp.json()[0]["translations"][0]["text"]


def generate_answer(query: str, context_chunks: list[dict], language: str = "English") -> str:
    """Use GPT-4.1 to synthesize an answer in English, then translate via Azure Translator."""
    client = get_openai_client()

    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        context_parts.append(
            f"[Source {i} – Page {chunk['page_number']}]\n{chunk['content']}"
        )
    context_text = "\n\n---\n\n".join(context_parts)

    system_prompt = (
        "You are a helpful assistant that answers questions based on provided document excerpts. "
        "Always cite your sources using the [Source N – Page P] references provided. "
        "If the answer is not found in the provided context, say so clearly. "
        "Always respond in English."
    )

    user_prompt = f"""Context from the document:

{context_text}

---

Question: {query}

Provide a comprehensive answer with citations referencing the source numbers and page numbers above."""

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


# --------------- Speech ---------------
def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe WAV audio bytes to text using Azure Speech Service."""
    if not SPEECH_SDK_AVAILABLE:
        raise RuntimeError("Install azure-cognitiveservices-speech to use voice input.")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language = "en-US"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        audio_config = speechsdk.AudioConfig(filename=tmp_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        result = recognizer.recognize_once_async().get()
        # Explicitly release SDK objects so the file handle is freed on Windows
        del recognizer
        del audio_config
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            return ""
        else:
            cancellation = result.cancellation_details
            raise RuntimeError(
                f"Speech recognition failed: {result.reason}. "
                f"{cancellation.error_details if cancellation else ''}"
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # Windows may still hold the handle briefly; temp dir cleanup handles it


def summarize_for_speech(answer: str, language: str = "English") -> str:
    """Generate a concise spoken summary in English via GPT, then translate via Azure Translator."""
    client = get_openai_client()
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You convert a written answer into a short script for a voice assistant "
                    "to read aloud. Rules:\n"
                    "- Write exactly ONE paragraph with 2-4 flowing sentences.\n"
                    "- Use simple, natural spoken English — as if explaining to a friend.\n"
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


def synthesize_speech(text: str, language: str = "English") -> io.BytesIO:
    """Synthesize text to a WAV audio stream using the Azure Speech Service.

    Selects the appropriate Neural voice for the given language.
    """
    if not SPEECH_SDK_AVAILABLE:
        raise RuntimeError("Install azure-cognitiveservices-speech to use voice output.")

    lang_cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )
    speech_config.speech_synthesis_voice_name = lang_cfg["voice"]

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_stream = io.BytesIO(result.audio_data)
        audio_stream.seek(0)
        return audio_stream

    cancellation = result.cancellation_details
    raise RuntimeError(
        f"Speech synthesis failed: {result.reason}. "
        f"{cancellation.error_details if cancellation else ''}"
    )


# --------------- Streamlit UI ---------------
def main():
    st.set_page_config(page_title="RAG Document Assistant", page_icon="📄", layout="wide")

    # --------------- Session state init ---------------
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "indexed_docs" not in st.session_state:
        # Each entry: {"name": str, "pages": int, "chunks": int}
        st.session_state.indexed_docs = []
    if "voice_query" not in st.session_state:
        st.session_state.voice_query = None
    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None
    if "output_language" not in st.session_state:
        st.session_state.output_language = "English"

    speech_enabled = SPEECH_SDK_AVAILABLE and bool(AZURE_SPEECH_KEY and AZURE_SPEECH_REGION)

    # ================================================================
    # LEFT PANEL — Sidebar
    # ================================================================
    with st.sidebar:
        st.title("📄 Document Manager")

        # ---- Configuration status ----
        config_ok = all(
            [
                DOC_INTELLIGENCE_ENDPOINT,
                DOC_INTELLIGENCE_KEY,
                SEARCH_ENDPOINT,
                SEARCH_KEY,
                AZURE_OPENAI_ENDPOINT,
                AZURE_OPENAI_KEY,
            ]
        )
        if not config_ok:
            st.error("⚠️ Missing Azure configuration")
            missing = []
            if not DOC_INTELLIGENCE_ENDPOINT:
                missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            if not DOC_INTELLIGENCE_KEY:
                missing.append("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            if not SEARCH_ENDPOINT:
                missing.append("AZURE_SEARCH_ENDPOINT")
            if not SEARCH_KEY:
                missing.append("AZURE_SEARCH_KEY")
            if not AZURE_OPENAI_ENDPOINT:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not AZURE_OPENAI_KEY:
                missing.append("AZURE_OPENAI_KEY")
            for m in missing:
                st.code(m)
            st.stop()

        with st.expander("⚙️ Service Info", expanded=False):
            st.markdown(f"**Index:** `{SEARCH_INDEX_NAME}`")
            st.markdown(f"**LLM:** `{AZURE_OPENAI_DEPLOYMENT}`")
            st.markdown(f"**Embeddings:** `{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}`")
            if speech_enabled:
                st.markdown(f"**Speech region:** `{AZURE_SPEECH_REGION}`")

        # ---- Speech toggle ----
        if speech_enabled:
            st.toggle("🔊 Read answers aloud", value=True, key="tts_enabled")
        else:
            missing_speech = []
            if not SPEECH_SDK_AVAILABLE:
                missing_speech.append("SDK not installed")
            if not AZURE_SPEECH_KEY:
                missing_speech.append("AZURE_SPEECH_KEY missing")
            if not AZURE_SPEECH_REGION:
                missing_speech.append("AZURE_SPEECH_REGION missing")
            st.caption("🎤 Voice disabled — " + " · ".join(missing_speech))

        # ---- Output language selector ----
        st.subheader("🌐 Output Language")
        st.selectbox(
            "AI answers and speech in:",
            options=list(LANGUAGE_CONFIG.keys()),
            key="output_language",
            help="The AI answer and spoken summary will be delivered in the selected language via Azure Translator.",
        )
        selected_lang = st.session_state.get("output_language", "English")
        if selected_lang != "English":
            if AZURE_TRANSLATOR_KEY:
                st.caption("✅ Azure Translator connected")
            else:
                st.warning(
                    "⚠️ AZURE_TRANSLATOR_KEY not set. "
                    "Translation will be skipped — answers will remain in English.",
                    icon="⚠️",
                )

        st.divider()

        # ---- Indexed documents this session ----
        st.subheader("📚 Indexed Documents")
        if st.session_state.indexed_docs:
            for doc in st.session_state.indexed_docs:
                st.markdown(
                    f"✅ **{doc['name']}**  \n"
                    f"<small>{doc['pages']} pages · {doc['chunks']} chunks</small>",
                    unsafe_allow_html=True,
                )
            if st.button("🗑️ Clear chat history", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        else:
            st.info(
                "No documents uploaded this session.\n\n"
                "You can still ask questions about documents already in the index.",
                icon="ℹ️",
            )

        st.divider()

        # ---- Upload & Index ----
        st.subheader("➕ Upload New Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload a PDF to analyze with Document Intelligence and index into AI Search.",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            st.caption(f"📎 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

            if st.button("🚀 Analyze & Index", type="primary", use_container_width=True):
                pdf_bytes = uploaded_file.read()
                progress_bar = st.progress(0, text="Starting…")
                status = st.empty()

                # Step 1 — Document Intelligence
                progress_bar.progress(10, text="🔍 Analyzing with Document Intelligence…")
                try:
                    pages = analyze_pdf(pdf_bytes)
                except Exception as e:
                    st.error(f"Document Intelligence error: {e}")
                    st.stop()

                status.success(f"Extracted **{len(pages)}** page(s)")

                with st.expander("📋 Preview extracted text", expanded=False):
                    for page in pages[:3]:
                        st.markdown(f"**Page {page['page_number']}**")
                        st.text(
                            page["content"][:400]
                            + ("…" if len(page["content"]) > 400 else "")
                        )
                        st.divider()

                # Step 2 — Chunking
                progress_bar.progress(40, text="✂️ Splitting into chunks…")
                chunks = chunk_pages(pages)
                status.success(f"Created **{len(chunks)}** chunks")

                # Step 3 — Ensure index
                progress_bar.progress(55, text="🏗️ Ensuring search index exists…")
                try:
                    ensure_search_index()
                except Exception as e:
                    st.error(f"Search index error: {e}")
                    st.stop()

                # Step 4 — Embed & upload
                progress_bar.progress(70, text="📊 Generating embeddings & uploading…")
                try:
                    upload_chunks_to_index(chunks)
                except Exception as e:
                    st.error(f"Indexing error: {e}")
                    st.stop()

                progress_bar.progress(100, text="✅ Done!")
                st.success(f"🎉 **{uploaded_file.name}** indexed successfully!")

                st.session_state.indexed_docs.append(
                    {
                        "name": uploaded_file.name,
                        "pages": len(pages),
                        "chunks": len(chunks),
                    }
                )
                st.rerun()

    # ================================================================
    # CENTER PANEL — Chat
    # ================================================================
    st.title("💬 Document Assistant")

    if st.session_state.indexed_docs:
        doc_names = ", ".join(d["name"] for d in st.session_state.indexed_docs)
        st.caption(
            f"Chatting with: **{doc_names}** · "
            "Type or speak your question below."
            if speech_enabled
            else f"Chatting with: **{doc_names}**"
        )
    else:
        st.caption(
            "Ask questions about documents already in the index. "
            "Upload new documents using the **Document Manager** on the left."
        )

    # ---- Chat history ----
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("📚 Sources & Citations"):
                    for src in msg["sources"]:
                        st.markdown(
                            f"**Page {src['page_number']}** · relevance score: `{src['score']:.4f}`"
                        )
                        st.text(src["content"][:300])
                        st.divider()
            if msg["role"] == "assistant" and msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
    # ---- Voice input ----
    active_query = None
    if speech_enabled:
        st.markdown(
            "**🎤 Voice Input** — Click the microphone, speak, then click stop:",
            help="Your speech will be transcribed and used as the query.",
        )
        audio_input = st.audio_input(
            "Record your question", key="audio_recorder", label_visibility="collapsed"
        )
        if audio_input is not None:
            audio_bytes = audio_input.read()
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            if audio_hash != st.session_state.last_audio_hash:
                st.session_state.last_audio_hash = audio_hash
                with st.spinner("🎧 Transcribing your speech…"):
                    try:
                        transcribed = transcribe_audio(audio_bytes)
                        if transcribed:
                            st.session_state.voice_query = transcribed
                            st.info(f"🗣️ Heard: **{transcribed}**")
                        else:
                            st.warning("Could not understand the audio. Please try again.")
                    except Exception as e:
                        st.error(f"Speech transcription error: {e}")

    # Consume pending voice query
    if st.session_state.get("voice_query"):
        active_query = st.session_state.voice_query
        st.session_state.voice_query = None

    # ---- Text input (pinned to bottom by Streamlit) ----
    text_input = st.chat_input("Ask a question about your documents…")
    if text_input:
        active_query = text_input

    # ---- Process query ----
    if active_query:
        query = active_query
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Searching and generating answer…"):
                try:
                    search_results = hybrid_search(query, top_k=5)
                    if not search_results:
                        answer = (
                            "I couldn't find any relevant content in the index for your question. "
                            "Try uploading and indexing the relevant document first."
                        )
                        sources = []
                    else:
                        answer = generate_answer(
                            query,
                            search_results,
                            language=st.session_state.get("output_language", "English"),
                        )
                        sources = search_results
                except Exception as e:
                    answer = f"An error occurred: {e}"
                    sources = []

            st.markdown(answer)

            if sources:
                with st.expander("📚 Sources & Citations"):
                    for src in sources:
                        st.markdown(
                            f"**Page {src['page_number']}** · relevance score: `{src['score']:.4f}`"
                        )
                        st.text(src["content"][:300])
                        st.divider()

            # ---- TTS ----
            audio_data = None
            if speech_enabled and st.session_state.get("tts_enabled", True):
                with st.spinner("🔊 Generating spoken summary…"):
                    try:
                        selected_lang = st.session_state.get("output_language", "English")
                        speech_summary = summarize_for_speech(answer, language=selected_lang)
                        audio_data = synthesize_speech(speech_summary, language=selected_lang)
                        st.audio(audio_data, format="audio/wav", autoplay=True)
                    except Exception as e:
                        st.warning(f"Text-to-speech unavailable: {e}")

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources, "audio": audio_data}
        )


if __name__ == "__main__":
    main()
