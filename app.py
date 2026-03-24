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
from services.llm import generate_answer, summarize_for_speech
from services.search import hybrid_search
from services.search_index import ensure_search_index, upload_chunks_to_index
from services.speech import SPEECH_SDK_AVAILABLE, synthesize_speech, transcribe_audio


def main():
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

    _render_chat_history()

    active_query = _collect_voice_query(speech_enabled)
    text_input = st.chat_input("Ask a question about your documents…")
    if text_input:
        active_query = text_input

    if active_query:
        _process_query(active_query, speech_enabled)


# ================================================================
# Sidebar helper renderers
# ================================================================

def _render_config_check() -> None:
    """Stop the app with a clear error if mandatory Azure credentials are missing."""
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
            "You can still query documents already in the index.",
            icon="ℹ️",
        )


def _render_upload_section() -> None:
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
    chunks = chunk_pages(pages)
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
    """Render the audio recorder widget and return a transcribed query if available."""
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
    """Run the full RAG pipeline for a user query and render the response."""
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
