# RAG Document Assistant — Recreation Prompts

Three sequential prompts to recreate this codebase from scratch using an AI model.

---

## Prompt 1 — Core RAG Backend Pipeline (Config, Document Intelligence, Chunking, Embeddings, Search Index, Hybrid Search)

Build the backend services for a Python RAG (Retrieval Augmented Generation) application that processes PDF documents and indexes them into Azure AI Search for hybrid retrieval. The project must use `python-dotenv` for configuration. Do NOT build any UI yet — only the service modules and configuration.

**Project structure:**
```
app.py              # (empty placeholder for now)
config.py           # all configuration
requirements.txt
services/
    __init__.py
    document_intelligence.py
    chunker.py
    embeddings.py
    search_index.py
    search.py
```

**1. `config.py` — Centralized configuration from environment variables:**
- Load `.env` via `python-dotenv`.
- Expose constants for: Azure Document Intelligence (endpoint + key), Azure AI Search (endpoint + key + index name defaulting to `"rag-documents"`), Azure OpenAI (endpoint, key, chat deployment defaulting to `"gpt-4.1"`, embedding deployment defaulting to `"text-embedding-ada-002"`, API version defaulting to `"2025-03-01-preview"`), Azure Speech (key + region), Azure Translator (key + region).
- Include a `LANGUAGE_CONFIG` dictionary mapping display names to translator codes, Azure Neural voice names, and speech locales for: English (`en-US-JennyNeural`), Hindi (`hi-IN-SwaraNeural`), French (`fr-FR-DeniseNeural`), Telugu (`te-IN-ShrutiNeural`).

**2. `services/document_intelligence.py` — PDF text extraction:**
- Function `analyze_pdf(pdf_bytes: bytes) -> list[dict]` that uses `azure-ai-documentintelligence` SDK.
- Use the `"prebuilt-layout"` model via `begin_analyze_document` with `AnalyzeDocumentRequest(bytes_source=pdf_bytes)`.
- Return a list of dicts, each with `page_number` (int) and `content` (str, newline-joined lines from `page.lines`).

**3. `services/chunker.py` — Overlapping character-level text chunking:**
- Function `chunk_pages(pages: list[dict], chunk_size: int = 1000, overlap: int = 200) -> list[dict]`.
- For each page, slide a window of `chunk_size` characters with `chunk_size - overlap` step.
- Skip pages with empty/whitespace-only content.
- Each chunk dict has: `id` (first 16 hex chars of SHA-256 of `"{page_number}-{start_offset}"`), `content`, `page_number`, `offset`.

**4. `services/embeddings.py` — Azure OpenAI embedding generation:**
- Function `generate_embeddings(texts: list[str]) -> list[list[float]]` using the `openai` Python SDK's `AzureOpenAI` client.
- Call `client.embeddings.create(input=texts, model=EMBEDDING_DEPLOYMENT)`.
- Return the list of embedding vectors.

**5. `services/search_index.py` — Index creation and document upload:**
- Function `ensure_search_index()` that creates the Azure AI Search index if it doesn't already exist. The index schema must have these fields:
  - `id`: String, key, filterable
  - `content`: String, searchable
  - `page_number`: Int32, filterable
  - `offset`: Int32, filterable
  - `content_vector`: Collection(Single), searchable, 3072 dimensions, using HNSW algorithm with a vector search profile named `"default-profile"` and algorithm config named `"default-hnsw"`.
- Function `upload_chunks_to_index(chunks: list[dict])` that: generates embeddings in batches of 16, attaches the embedding to each chunk document as `content_vector`, and uploads to the index in batches of 100.

**6. `services/search.py` — Hybrid search retrieval:**
- Function `hybrid_search(query: str, top_k: int = 5) -> list[dict]`.
- Generate the query's embedding vector, then call `search_client.search()` with both `search_text=query` and a `VectorizedQuery` object targeting `"content_vector"` with `k_nearest_neighbors=top_k`.
- Select fields: id, content, page_number. Return dicts with those fields plus `score` from `@search.score`.

**7. `requirements.txt`:**
```
streamlit>=1.40.0
python-dotenv>=1.0.0
azure-ai-documentintelligence>=1.0.0
azure-search-documents>=11.6.0
openai>=1.60.0
azure-core>=1.32.0
azure-cognitiveservices-speech>=1.41.0
azure-ai-translation-text>=1.0.0
```

Use `azure-search-documents` SDK types (`SearchClient`, `SearchIndexClient`, `SearchField`, `VectorSearch`, `HnswAlgorithmConfiguration`, etc.) and `AzureKeyCredential` for authentication everywhere. Keep each module focused on a single responsibility with clean imports from `config.py`.

---

## Prompt 2 — Streamlit Chat UI & LLM Answer Generation with Citations

Using the backend services created previously (`services/document_intelligence.py`, `services/chunker.py`, `services/search_index.py`, `services/search.py`, `services/embeddings.py`, and `config.py`), build the Streamlit frontend (`app.py`) and the LLM answer generation module (`services/llm.py`). Do NOT implement speech or translation features yet — stub out translation as a pass-through.

**1. `services/llm.py` — GPT-4.1 answer generation with citations:**
- Helper `_get_client()` returning an `AzureOpenAI` client.
- Function `generate_answer(query: str, context_chunks: list[dict], language: str = "English") -> str`:
  - Format each chunk as `[Source {i} - Page {page_number}]\n{content}`, joined by `\n\n---\n\n`.
  - System prompt instructs the model: answer based on provided excerpts, cite using `[Source N - Page P]` references, say clearly if the answer isn't in the context, always respond in English.
  - User prompt includes the formatted context + the question + instruction to provide citations.
  - Use `temperature=0.3`, `max_tokens=1500`.
  - Pass the English answer through a `translate_text(answer, language)` call (initially a no-op).
- Function `summarize_for_speech(answer: str, language: str = "English") -> str`:
  - Takes a written answer and condenses it into a natural spoken paragraph (2-4 sentences, no bullet points, no formatting markers, no citation markers).
  - System prompt must explicitly forbid: bullet points, numbered lists, citation markers like `[Source 1]`, asterisks, dashes, colons at line starts, abbreviations without spelling out, and starting with filler phrases like "Sure", "Here is", "In summary".
  - Use `temperature=0.4`, `max_tokens=300`.
  - Also pass through `translate_text()`.

**2. `app.py` — Full Streamlit application:**
- **Page config:** Title "RAG Document Assistant", icon "📄", wide layout.
- **Session state keys:** `messages` (list), `indexed_docs` (list), `voice_query` (None), `last_audio_hash` (None), `output_language` ("English").
- **Sidebar ("📄 Document Manager"):**
  - **Config check:** Validate that all required Azure env vars (Doc Intelligence endpoint/key, Search endpoint/key, OpenAI endpoint/key) are set. If any are missing, show `st.error` listing them and call `st.stop()`.
  - **Service Info expander:** Show the index name, LLM deployment, embedding deployment.
  - **Speech toggle:** A `st.toggle("🔊 Read answers aloud")` if speech is enabled; otherwise a caption explaining why it's disabled (SDK not installed / keys missing).
  - **Language selector:** `st.selectbox` with the keys of `LANGUAGE_CONFIG`. Show "✅ Azure Translator connected" if the translator key is set and a non-English language is selected; show a warning if it's missing.
  - **Indexed Documents section:** List all documents uploaded this session (name, pages, chunks). If any exist, offer a "🗑️ Clear chat history" button. If none, show an info box saying users can still query existing index content.
  - **Upload section:** `st.file_uploader` for PDFs. On "🚀 Analyze & Index" button press, run the full pipeline with a `st.progress` bar showing stages: Document Intelligence (10%), chunking (40%), ensure index (55%), embed+upload (70%), done (100%). Show a preview expander with the extracted text from the first 3 pages (400-char truncation). On success, append to `indexed_docs` and `st.rerun()`.
- **Center — Chat area:**
  - Title "💬 Document Assistant" with a caption showing which documents are loaded.
  - Render full chat history from `st.session_state.messages`. For assistant messages, show an expandable "📚 Sources & Citations" section with page number, relevance score (4 decimal places), and content preview (300 chars). Also replay any stored audio.
  - `st.chat_input("Ask a question about your documents…")` for text queries.
  - **Query processing (`_process_query`):** Append user message → call `hybrid_search(query, top_k=5)` → if no results, return a "no content found" message → otherwise call `generate_answer(query, results, language)` → display answer + sources expander → append assistant message with content, sources, and audio data to session state.

Structure `app.py` with a `main()` function and private helper functions prefixed with `_` (e.g., `_render_config_check`, `_render_speech_toggle`, `_render_language_selector`, `_render_indexed_docs`, `_render_upload_section`, `_render_chat_history`, `_process_query`). Use `if __name__ == "__main__": main()`.

---

## Prompt 3 — Multi-Language Translation & Speech (STT + TTS) Integration

Add multi-language translation and full speech capabilities (speech-to-text and text-to-speech) to the RAG Document Assistant built in the previous prompts. This involves creating two new service modules and wiring them into the existing `app.py` and `services/llm.py`.

**1. `services/translation.py` — Azure Translator integration:**
- Use the `azure-ai-translation-text` SDK (`TextTranslationClient`).
- Helper `_get_client()` that creates a `TextTranslationClient` with `AzureKeyCredential` and the configured `AZURE_TRANSLATOR_REGION`.
- Function `translate_text(text: str, language: str) -> str`:
  - Look up the `translator_code` from `LANGUAGE_CONFIG` for the given language display name (default to English config if unknown).
  - Return the original text unchanged if the target code is `"en"` or if `AZURE_TRANSLATOR_KEY` is not configured (graceful fallback).
  - Otherwise call `client.translate(body=[text], to_language=[target_code], from_language="en")` and return the first translation.
- Update `services/llm.py` to import and use `translate_text` from this module. The pattern is: **always generate in English first with GPT-4.1, then translate the final output** (both for `generate_answer` and `summarize_for_speech`).

**2. `services/speech.py` — Azure Speech Service (STT + TTS):**
- Wrap the `azure-cognitiveservices-speech` import in a try/except. Export a `SPEECH_SDK_AVAILABLE` boolean flag set to `True` if the import succeeds, `False` otherwise. The rest of the app uses this flag for graceful degradation.
- Function `transcribe_audio(audio_bytes: bytes) -> str`:
  - Write the audio bytes to a temporary `.wav` file (use `tempfile.NamedTemporaryFile` with `delete=False`).
  - Create `SpeechConfig` with the configured subscription key and region, set `speech_recognition_language="en-US"`.
  - Create `AudioConfig` from the temp file, then `SpeechRecognizer`, and call `recognize_once_async().get()`.
  - **Critical for Windows:** explicitly `del recognizer` and `del audio_config` before attempting to `os.unlink` the temp file (to release the file handle). Wrap the unlink in a try/except `OSError` in a `finally` block.
  - Return the recognized text on `RecognizedSpeech`, empty string on `NoMatch`, raise `RuntimeError` with cancellation details on any other reason.
- Function `synthesize_speech(text: str, language: str = "English") -> io.BytesIO`:
  - Look up the Neural voice name from `LANGUAGE_CONFIG` (e.g., `en-US-JennyNeural`, `hi-IN-SwaraNeural`).
  - Set output format to `Riff24Khz16BitMonoPcm`.
  - Create `SpeechSynthesizer` with `audio_config=None` (in-memory synthesis).
  - Call `speak_text_async(text).get()`, on success wrap `result.audio_data` in a `BytesIO`, seek to 0, and return.
  - On failure, raise `RuntimeError` with cancellation details.

**3. Wire speech into `app.py`:**
- Import `SPEECH_SDK_AVAILABLE`, `synthesize_speech`, `transcribe_audio` from `services.speech`.
- Compute `speech_enabled = SPEECH_SDK_AVAILABLE and bool(AZURE_SPEECH_KEY and AZURE_SPEECH_REGION)`.
- **Voice input** (`_collect_voice_query` function):
  - Render `st.audio_input("Record your question")` only when speech is enabled.
  - Deduplicate audio submissions using an MD5 hash stored in `st.session_state.last_audio_hash` — skip processing if the hash matches the previous recording.
  - On new audio: transcribe with `transcribe_audio()`, store the result in `st.session_state.voice_query`, show the transcribed text with `st.info`, and return it as the active query.
- **TTS output** in `_process_query`:
  - After generating the written answer, if speech is enabled and the "Read answers aloud" toggle is on: call `summarize_for_speech(answer, language)` to get a TTS-friendly condensed version, then `synthesize_speech(summary, language)` to get WAV audio data.
  - Display with `st.audio(audio_data, format="audio/wav", autoplay=True)`.
  - Store the audio data in the message's session state so it replays when scrolling through chat history.
  - Wrap TTS in try/except and show `st.warning` on failure (non-blocking).
