"""
app.py — RAG Document Assistant — Streamlit application entry point.

This is the top-level module that wires together all backend services into a
browser-based conversational UI.  It is launched with::

    streamlit run app.py

Application layout
------------------
The UI is divided into two areas:

**Sidebar (left panel)**
    - Configuration health check (missing Azure credentials are displayed here
      and the app is halted).
    - Service info expander (shows index name, model names, and speech region).
    - Speech enable/disable toggle.
    - Output language selector (English / Hindi / French / Telugu).
    - List of documents indexed in the current session.
    - PDF upload & indexing widget.

**Main area (center)**
    - Chat tab: multi-turn conversation with the indexed documents, supporting
      both text and voice input.  Each assistant reply shows cited sources and
      optional audio playback.
    - Summary tab: one-click whole-document summary for any indexed document,
      with optional language translation.

RAG pipeline (triggered on document upload)
-------------------------------------------
1. ``analyze_pdf``           — Extract text per page via Document Intelligence.
2. ``chunk_pages``           — Slide a 1 000-char window with 200-char overlap.
3. ``ensure_search_index``   — Create the AI Search index if absent.
4. ``upload_chunks_to_index`` — Embed (ada-002) + upload to AI Search.

RAG pipeline (triggered on user question)
-----------------------------------------
1. ``hybrid_search``         — BM25 + HNSW vector retrieval (top 5 chunks).
2. ``generate_answer``       — GPT-4.1 synthesis with source citations.
3. ``translate_text``        — Optional Azure Translator post-processing.
4. ``summarize_for_speech``  + ``synthesize_speech`` — Optional TTS playback.
"""

import hashlib

import streamlit as st

from config import (
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION,
    AZURE_TRANSLATOR_KEY,
    DOC_INTELLIGENCE_ENDPOINT,
    DOC_INTELLIGENCE_KEY,
    LANGUAGE_CONFIG,
    SEARCH_ENDPOINT,
    SEARCH_INDEX_NAME,
    SEARCH_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
)
from services.chunker import chunk_pages
from services.document_intelligence import analyze_pdf
from services.llm import generate_answer, generate_document_summary, summarize_for_speech
from services.search import hybrid_search, get_indexed_document_names, fetch_chunks_by_document
from services.search_index import ensure_search_index, upload_chunks_to_index
from services.speech import SPEECH_SDK_AVAILABLE, synthesize_speech, transcribe_audio


def main():
    """Application entry point — configure the page and render the full UI.

    Called directly by Streamlit when ``streamlit run app.py`` is executed.
    Responsible for:

    1. **Page configuration** — Sets the browser tab title, favicon, and wide
       layout via ``st.set_page_config``.
    2. **Session state initialisation** — Ensures all required session-state
       keys are present before any widget attempts to read them.  Streamlit's
       session state persists for the lifetime of the browser tab:

       - ``messages``        — Chat history list (role + content + sources + audio).
       - ``indexed_docs``    — Metadata for documents indexed this session.
       - ``voice_query``     — Transcribed speech query awaiting processing.
       - ``last_audio_hash`` — MD5 of the last audio recording; prevents the
         same recording from being transcribed twice on Streamlit reruns.
       - ``output_language`` — Currently selected output language.
       - ``document_summary`` — Cached summary for the selected document.

    3. **Speech availability detection** — Determines whether voice features
       should be shown based on SDK availability and credential presence.

    4. **Sidebar rendering** — Delegates to helper functions for each sidebar
       section (config check, service info, speech toggle, language selector,
       indexed doc list, upload widget).

    5. **Main content rendering** — Renders the chat tab (history + input +
       RAG pipeline) and the summary tab.
    """
    st.set_page_config(page_title="RAG Document Assistant", page_icon="📄", layout="wide")

    # --------------- Session state ---------------
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "indexed_docs" not in st.session_state:
        st.session_state.indexed_docs = []
    if "voice_query" not in st.session_state:
        st.session_state.voice_query = None
    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None
    if "output_language" not in st.session_state:
        st.session_state.output_language = "English"
    if "document_summary" not in st.session_state:
        st.session_state.document_summary = None
    if "podcast_audio" not in st.session_state:
        st.session_state.podcast_audio = None
    if "podcast_timing" not in st.session_state:
        st.session_state.podcast_timing = None
    if "podcast_segments" not in st.session_state:
        st.session_state.podcast_segments = None

    speech_enabled = SPEECH_SDK_AVAILABLE and bool(AZURE_SPEECH_KEY and AZURE_SPEECH_REGION)

    # ================================================================
    # SIDEBAR
    # ================================================================
    with st.sidebar:
        st.title("📄 Document Manager")

        _render_config_check()

        with st.expander("⚙️ Service Info", expanded=False):
            st.markdown(f"**Index:** `{SEARCH_INDEX_NAME}`")
            st.markdown(f"**LLM:** `{AZURE_OPENAI_DEPLOYMENT}`")
            st.markdown(f"**Embeddings:** `{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}`")
            if speech_enabled:
                st.markdown(f"**Speech region:** `{AZURE_SPEECH_REGION}`")

        _render_speech_toggle(speech_enabled)
        _render_language_selector()

        st.divider()
        _render_indexed_docs()

        st.divider()
        _render_upload_section()

    # ================================================================
    # CENTER — Chat
    # ================================================================
    st.title("💬 Document Assistant")

    if st.session_state.indexed_docs:
        doc_names = ", ".join(d["name"] for d in st.session_state.indexed_docs)
        st.caption(
            f"Chatting with: **{doc_names}** · Type or speak your question below."
            if speech_enabled
            else f"Chatting with: **{doc_names}**"
        )
    else:
        st.caption(
            "Ask questions about documents already in the index. "
            "Upload new documents using the **Document Manager** on the left."
        )

    tab_chat, tab_summary = st.tabs(["💬 Chat", "📝 Summary"])

    with tab_chat:
        _render_chat_history()

        active_query = _collect_voice_query(speech_enabled)
        text_input = st.chat_input("Ask a question about your documents…")
        if text_input:
            active_query = text_input

        if active_query:
            _process_query(active_query, speech_enabled)

    with tab_summary:
        try:
            doc_names = get_indexed_document_names()
        except Exception:
            doc_names = []

        if doc_names:
            st.selectbox(
                "Select a document to summarize",
                options=doc_names,
                key="summary_doc_select",
            )
            if st.button("📝 Generate Summary", type="primary", use_container_width=True):
                _generate_summary()

            if st.session_state.document_summary:
                st.divider()
                st.markdown(st.session_state.document_summary)
                if st.button("🗑️ Clear summary", key="clear_summary"):
                    st.session_state.document_summary = None
                    st.rerun()
        else:
            st.info(
                "No documents found in the index. Upload and index a document first.",
                icon="ℹ️",
            )   


# ================================================================
# Sidebar helper renderers
# ================================================================

def _render_config_check() -> None:
    """Validate that all mandatory Azure credentials are present; halt the app if not.

    Checks six environment variables that are unconditionally required for the
    core RAG pipeline (Document Intelligence, AI Search, and Azure OpenAI).
    If any are missing, displays a styled error block in the sidebar listing
    the names of the missing variables, then calls ``st.stop()`` to prevent
    the rest of the application from rendering.

    This is the first thing rendered in the sidebar so users see a clear,
    actionable error message before any other UI element appears.  Once all
    variables are set in ``.env`` and the page is refreshed, the check passes
    silently.

    Missing variables checked:
        - ``AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT``
        - ``AZURE_DOCUMENT_INTELLIGENCE_KEY``
        - ``AZURE_SEARCH_ENDPOINT``
        - ``AZURE_SEARCH_KEY``
        - ``AZURE_OPENAI_ENDPOINT``
        - ``AZURE_OPENAI_KEY``
    """
    required = {
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": DOC_INTELLIGENCE_ENDPOINT,
        "AZURE_DOCUMENT_INTELLIGENCE_KEY": DOC_INTELLIGENCE_KEY,
        "AZURE_SEARCH_ENDPOINT": SEARCH_ENDPOINT,
        "AZURE_SEARCH_KEY": SEARCH_KEY,
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_KEY": AZURE_OPENAI_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        st.error("⚠️ Missing Azure configuration")
        for name in missing:
            st.code(name)
        st.stop()


def _render_speech_toggle(speech_enabled: bool) -> None:
    """Render the text-to-speech toggle or a disabled-reason caption in the sidebar.

    When all speech prerequisites are met (SDK installed + credentials present),
    renders a Streamlit ``st.toggle`` widget that lets users enable or disable
    "Read answers aloud" live text-to-speech playback.  The widget state is
    stored in ``st.session_state.tts_enabled``.

    When speech is not available, renders an informational caption instead of
    a toggle, listing the specific reasons why speech is disabled (missing SDK,
    missing API key, missing region).  This gives users clear guidance on what
    to install or configure to enable the feature.

    Args:
        speech_enabled (bool): Pre-computed flag indicating whether the Speech
            SDK is installed AND both ``AZURE_SPEECH_KEY`` and
            ``AZURE_SPEECH_REGION`` are configured.  Passed in from
            :func:`main` to avoid repeating the same checks.
    """
    if speech_enabled:
        st.toggle("🔊 Read answers aloud", value=True, key="tts_enabled")
    else:
        reasons = []
        if not SPEECH_SDK_AVAILABLE:
            reasons.append("SDK not installed")
        if not AZURE_SPEECH_KEY:
            reasons.append("AZURE_SPEECH_KEY missing")
        if not AZURE_SPEECH_REGION:
            reasons.append("AZURE_SPEECH_REGION missing")
        st.caption("🎤 Voice disabled — " + " · ".join(reasons))


def _render_language_selector() -> None:
    """Render the output language dropdown and Translator status in the sidebar.

    Displays a ``st.selectbox`` populated with the language display names from
    ``LANGUAGE_CONFIG`` (English, Hindi, French, Telugu).  The selected value
    is persisted in ``st.session_state.output_language`` and read by
    :func:`_process_query`, :func:`_generate_summary`, and the TTS pipeline.

    If a non-English language is selected, also shows a status indicator:

    * Green checkmark (✅) with "Azure Translator connected" if
      ``AZURE_TRANSLATOR_KEY`` is set.
    * Orange warning (⚠️) explaining the key is missing and answers will
      remain in English if it is not.

    This lets users immediately understand whether their language selection
    will actually be applied before sending a question.
    """
    st.subheader("🌐 Output Language")
    st.selectbox(
        "AI answers and speech in:",
        options=list(LANGUAGE_CONFIG.keys()),
        key="output_language",
        help="Answers and spoken summaries are translated via Azure Translator.",
    )
    selected = st.session_state.get("output_language", "English")
    if selected != "English":
        if AZURE_TRANSLATOR_KEY:
            st.caption("✅ Azure Translator connected")
        else:
            st.warning(
                "⚠️ AZURE_TRANSLATOR_KEY not set — answers will remain in English.",
                icon="⚠️",
            )


def _render_indexed_docs() -> None:
    """Render the list of documents indexed during the current session.

    Displays each document as a labelled card with the filename, page count,
    and chunk count collected at upload time and stored in
    ``st.session_state.indexed_docs``.

    When at least one document is listed, also renders a "Clear chat history"
    button that wipes ``st.session_state.messages`` and
    ``st.session_state.document_summary`` and triggers a rerun.  This lets
    users start a fresh conversation without re-uploading their documents.

    When no documents have been uploaded in the current session, shows an info
    box reminding the user that they can still query documents that were
    indexed in a previous session (the AI Search index persists across
    sessions).
    """
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
            st.session_state.document_summary = None
            st.rerun()
    else:
        st.info(
            "No documents uploaded this session.\n\n"
            "You can still query documents already in the index.",
            icon="ℹ️",
        )


def _generate_summary() -> None:
    """Fetch all chunks for the selected document and generate a full-document summary.

    Triggered when the user clicks "Generate Summary" in the Summary tab.
    Reads the selected document name from ``st.session_state.summary_doc_select``
    and the desired output language from ``st.session_state.output_language``.

    Execution steps:
        1. Call :func:`~services.search.fetch_chunks_by_document` to retrieve
           all indexed chunks for the document in reading order.
        2. Call :func:`~services.llm.generate_document_summary` with the chunks
           and target language.
        3. Store the result in ``st.session_state.document_summary`` and call
           ``st.rerun()`` so the summary renders in the tab.

    Error handling:
        - Warns the user (via ``st.warning``) if no chunks are found for the
          selected document (e.g., if the document was deleted from the index).
        - Catches and displays any exception from the service calls via
          ``st.error`` without crashing the app.
    """
    document_name = st.session_state.get("summary_doc_select")
    if not document_name:
        st.warning("Please select a document first.")
        return
    language = st.session_state.get("output_language", "English")
    with st.spinner("📝 Fetching document chunks and generating summary…"):
        try:
            chunks = fetch_chunks_by_document(document_name)
            if not chunks:
                st.warning("No chunks found for this document.")
                return
            summary = generate_document_summary(chunks, language=language)
            st.session_state.document_summary = summary
            st.rerun()
        except Exception as e:
            st.error(f"Summary generation error: {e}")


def _render_upload_section() -> None:
    """Render the PDF upload widget and drive the full document ingestion pipeline.

    Displays a ``st.file_uploader`` that accepts PDF files.  When a file is
    selected and the user clicks "Analyze & Index", this function orchestrates
    the complete ingestion pipeline with a live progress bar:

    +--------+-------------------------------------------------------+---------+
    | Step   | Action                                                | Progress|
    +========+=======================================================+=========+
    | 1      | ``analyze_pdf`` — Send PDF bytes to Document          | 10%     |
    |        | Intelligence and extract per-page text.               |         |
    +--------+-------------------------------------------------------+---------+
    | 2      | Preview extracted text in a collapsible expander      | —       |
    |        | (first 3 pages, up to 400 chars each).                |         |
    +--------+-------------------------------------------------------+---------+
    | 3      | ``chunk_pages`` — Split pages into overlapping        | 40%     |
    |        | 1 000-char chunks with 200-char overlap.              |         |
    +--------+-------------------------------------------------------+---------+
    | 4      | ``ensure_search_index`` — Create the Azure AI Search  | 55%     |
    |        | index if it does not already exist.                   |         |
    +--------+-------------------------------------------------------+---------+
    | 5      | ``upload_chunks_to_index`` — Embed all chunks with    | 70%     |
    |        | ada-002 and upload to the search index.               |         |
    +--------+-------------------------------------------------------+---------+
    | 6      | Success banner + session state update.                | 100%    |
    +--------+-------------------------------------------------------+---------+

    On success, appends a metadata dict (name, pages, chunks) to
    ``st.session_state.indexed_docs`` and calls ``st.rerun()`` so the sidebar
    document list refreshes immediately.

    Errors at any step are displayed via ``st.error`` and ``st.stop()`` halts
    processing at that stage without affecting already-indexed documents.
    """
    st.subheader("➕ Upload New Document")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Analyzed with Document Intelligence, chunked, embedded, and indexed into AI Search.",
        label_visibility="collapsed",
    )
    if uploaded_file is None:
        return

    st.caption(f"📎 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    if not st.button("🚀 Analyze & Index", type="primary", use_container_width=True):
        return

    pdf_bytes = uploaded_file.read()
    progress = st.progress(0, text="Starting…")
    status = st.empty()

    progress.progress(10, text="🔍 Analyzing with Document Intelligence…")
    try:
        pages = analyze_pdf(pdf_bytes)
    except Exception as e:
        st.error(f"Document Intelligence error: {e}")
        st.stop()
    status.success(f"Extracted **{len(pages)}** page(s)")

    with st.expander("📋 Preview extracted text", expanded=False):
        for page in pages[:3]:
            st.markdown(f"**Page {page['page_number']}**")
            st.text(page["content"][:400] + ("…" if len(page["content"]) > 400 else ""))
            st.divider()

    progress.progress(40, text="✂️ Splitting into chunks…")
    chunks = chunk_pages(pages, document_name=uploaded_file.name)
    status.success(f"Created **{len(chunks)}** chunks")

    progress.progress(55, text="🏗️ Ensuring search index exists…")
    try:
        ensure_search_index()
    except Exception as e:
        st.error(f"Search index error: {e}")
        st.stop()

    progress.progress(70, text="📊 Generating embeddings & uploading…")
    try:
        upload_chunks_to_index(chunks)
    except Exception as e:
        st.error(f"Indexing error: {e}")
        st.stop()

    progress.progress(100, text="✅ Done!")
    st.success(f"🎉 **{uploaded_file.name}** indexed successfully!")
    st.session_state.indexed_docs.append(
        {"name": uploaded_file.name, "pages": len(pages), "chunks": len(chunks)}
    )
    st.rerun()


# ================================================================
# Chat helpers
# ================================================================

def _render_chat_history() -> None:
    """Re-render the full conversation history from session state.

    Iterates over ``st.session_state.messages`` and renders each message in a
    ``st.chat_message`` container with the appropriate role icon (user or
    assistant).  For assistant messages, additionally renders:

    - A collapsible "Sources & Citations" expander listing each source chunk's
      page number, RRF relevance score, and the first 300 characters of content.
    - An audio player (``st.audio``) if a WAV audio stream was generated for
      that response (i.e., when TTS was enabled).

    This function is called at the top of the chat tab on every Streamlit
    rerun so the full history is always visible when the page refreshes after
    a new message is added.
    """
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


def _collect_voice_query(speech_enabled: bool) -> str | None:
    """Render the audio recorder widget and return a transcribed query if new audio is available.

    Displays a ``st.audio_input`` recorder widget when speech is enabled.  To
    prevent the same recording from being re-transcribed on every Streamlit
    rerun (Streamlit re-executes the entire script on each interaction), the
    function computes an **MD5 hash** of the raw audio bytes and compares it
    to ``st.session_state.last_audio_hash``.  Only if the hash is new does it
    proceed to transcription.

    Transcription is delegated to :func:`~services.speech.transcribe_audio`.
    The transcribed text is displayed to the user in an info box ("Heard: ..."),
    stored temporarily in ``st.session_state.voice_query``, cleared from
    session state before returning, and returned as the function result so it
    can be processed by :func:`_process_query`.

    Args:
        speech_enabled (bool): Whether voice input is available (SDK installed
            and ``AZURE_SPEECH_KEY`` / ``AZURE_SPEECH_REGION`` are configured).
            If ``False``, the function returns ``None`` immediately without
            rendering any widget.

    Returns:
        str | None: The transcribed question as a plain string if new audio
            was recorded and transcribed successfully.  Returns ``None`` if
            speech is disabled, no audio has been recorded, the same audio
            was already processed, or transcription yielded an empty result.
    """
    if not speech_enabled:
        return None

    st.markdown(
        "**🎤 Voice Input** — Click the microphone, speak, then click stop:",
        help="Your speech will be transcribed and used as the query.",
    )
    audio_input = st.audio_input(
        "Record your question", key="audio_recorder", label_visibility="collapsed"
    )
    if audio_input is None:
        return None

    audio_bytes = audio_input.read()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    if audio_hash == st.session_state.last_audio_hash:
        return None

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

    if st.session_state.get("voice_query"):
        query = st.session_state.voice_query
        st.session_state.voice_query = None
        return query
    return None


def _process_query(query: str, speech_enabled: bool) -> None:
    """Execute the full RAG pipeline for a user query and stream the response to the UI.

    This is the core request-handling function.  It is called whenever a new
    query is available — whether typed in the chat input or transcribed from
    voice.

    Pipeline steps:
        1. **Append user message** — Adds the query to
           ``st.session_state.messages`` and renders it in a ``st.chat_message``
           bubble immediately.
        2. **Hybrid search** — Calls :func:`~services.search.hybrid_search`
           with ``top_k=5`` to retrieve the most relevant document chunks.
        3. **Answer generation** — Calls :func:`~services.llm.generate_answer`
           with the query, retrieved chunks, and the target language.  If no
           search results are found, returns a fallback "no content" message.
        4. **Source display** — Renders a collapsible "Sources & Citations"
           expander showing each source chunk's page number, score, and a
           300-character preview.
        5. **TTS (optional)** — If speech is enabled and the TTS toggle is on,
           calls :func:`~services.llm.summarize_for_speech` followed by
           :func:`~services.speech.synthesize_speech` to generate a WAV audio
           stream, which is auto-played via ``st.audio``.
        6. **Append assistant message** — Stores the answer, sources list, and
           audio data in ``st.session_state.messages`` so they persist across
           reruns and are rendered by :func:`_render_chat_history`.

    Error handling:
        - If ``hybrid_search`` raises an exception, the error message is shown
          as the assistant reply and sources are cleared.
        - TTS errors show a warning (``st.warning``) but do not affect the
          text answer.

    Args:
        query (str): The user's question — either from ``st.chat_input`` or
            from :func:`_collect_voice_query`.
        speech_enabled (bool): Whether voice output should be attempted after
            the answer is generated.
    """
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    language = st.session_state.get("output_language", "English")

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
                    answer = generate_answer(query, search_results, language=language)
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

        audio_data = None
        if speech_enabled and st.session_state.get("tts_enabled", True):
            with st.spinner("🔊 Generating spoken summary…"):
                try:
                    speech_summary = summarize_for_speech(answer, language=language)
                    audio_data = synthesize_speech(speech_summary, language=language)
                    st.audio(audio_data, format="audio/wav", autoplay=True)
                except Exception as e:
                    st.warning(f"Text-to-speech unavailable: {e}")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources, "audio": audio_data}
    )

if __name__ == "__main__":
    main()
