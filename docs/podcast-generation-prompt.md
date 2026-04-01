# 🎙️ Podcast Feature — GitHub Copilot Prompt

Use the prompt below in GitHub Copilot Chat to generate the podcast functionality for the RAG Document Assistant. Copy everything inside the fenced block and paste it into Copilot Chat.

---

## The Prompt

```text
I want to add a "Podcast" feature to our RAG Document Assistant Streamlit app. The feature lets a user select an indexed document, generates a podcast-style audio script from its content using Azure OpenAI, synthesizes the script into WAV audio using Azure Speech SDK, and plays it back with a synchronized, word-highlighted transcript.

Here is what already exists in the codebase that you should reuse (do NOT recreate these):

- `config.py` has: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, and a LANGUAGE_CONFIG dict that maps language names (e.g. "English", "Hindi") to objects with keys "translator_code", "voice" (Azure Neural voice name), and "speech_locale".
- `services/llm.py` has a `_get_client()` helper that returns an authenticated `AzureOpenAI` client, and existing functions `generate_answer`, `summarize_for_speech`, and `generate_document_summary`.
- `services/speech.py` has existing functions `transcribe_audio` and `synthesize_speech`, imports `azure.cognitiveservices.speech as speechsdk`, and exposes `SPEECH_SDK_AVAILABLE`.
- `services/search.py` has `get_indexed_document_names()` which returns a sorted list of document names, and `fetch_chunks_by_document(document_name)` which returns all chunks for a document as a list of dicts with keys: id, content, page_number, offset.
- `app.py` is the Streamlit app. It already has tabs for Chat and Summary. The output language is stored in `st.session_state.output_language`. A variable `speech_enabled` (bool) indicates if speech services are configured.

Please generate the following three pieces of code:

---

### 1. Add `generate_podcast_script()` to `services/llm.py`

Create a function `generate_podcast_script(chunks: list[dict], language: str = "English") -> list[dict]` that:
- Concatenates all chunk content with page numbers into a context block (same pattern as `generate_document_summary`).
- Calls Azure OpenAI with a system prompt instructing it to act as a "professional podcast scriptwriter" converting the document into a compelling single-host podcast script.
- The system prompt rules should be: produce 4-15 segments depending on document length; each segment 2-5 sentences of natural conversational speech; start with a welcoming intro naming the document topic; end with a closing/wrap-up; use transitions between segments; never use bullet points, numbered lists, citation markers, asterisks, or markdown; never use abbreviations without spelling them out; write as spoken language with contractions encouraged; return ONLY a valid JSON array of objects with keys "segment" (int, 1-based) and "text" (string); write in the specified language.
- Uses temperature=0.5 and max_tokens=4000.
- Parses the response as JSON (strip markdown code fences if the model wraps them).
- Returns the list of segment dicts.
- Uses the existing `_get_client()` helper and `AZURE_OPENAI_DEPLOYMENT` from config.

---

### 2. Add `synthesize_podcast()` and `_assign_segments()` to `services/speech.py`

Create a function `synthesize_podcast(segments: list[dict], language: str = "English") -> tuple[io.BytesIO, list[dict]]` that:
- Looks up the voice name and speech locale from `LANGUAGE_CONFIG` for the given language.
- Builds an SSML string that wraps all segment texts inside a single `<speak>` and `<voice>` element, with a `<break time="750ms"/>` pause after each segment. Escape XML special characters (&, <, >, ", ') in segment text.
- Sets output format to `Riff24Khz16BitMonoPcm`.
- Subscribes to the synthesizer's `synthesis_word_boundary` event to capture word-level timing. Each event should record: `word` (evt.text), `offset_ms` (evt.audio_offset / 10_000 to convert 100-ns ticks to ms), and `duration_ms` (evt.duration.total_seconds() * 1000).
- Uses `speak_ssml_async` with `audio_config=None` for in-memory output.
- On success, returns a tuple of (BytesIO WAV audio stream seeked to 0, list of timing dicts).
- After synthesis, calls `_assign_segments()` to add a `segment_index` to each timing entry.

Also create a helper `_assign_segments(timing_data: list[dict], segment_texts: list[str]) -> None` that:
- Splits each segment text into words.
- Iterates through timing_data sequentially, assigning the current segment index to each word entry.
- Advances to the next segment when all words in the current segment have been matched.

---

### 3. Add the Podcast tab UI to `app.py`

Add these changes to `app.py`:

**Session state:** Initialize three new keys during app startup: `podcast_audio` (None), `podcast_timing` (None), `podcast_segments` (None).

**Tab:** Add a third tab "🎙️ Podcasts" alongside the existing Chat and Summary tabs. Inside it, call `_render_podcast_tab(speech_enabled)`.

**`_render_podcast_tab(speech_enabled)`:**
- If speech is not enabled, show a warning and return.
- Fetch document names using `get_indexed_document_names()`.
- If no documents, show an info message.
- Show a `st.selectbox` for document selection (key="podcast_doc_select").
- Show a "🎙️ Generate Podcast" primary button that calls `_generate_podcast()`.
- If podcast_audio and podcast_segments exist in session state, show a divider, call `_render_podcast_player()`, and show a "🗑️ Clear podcast" button that resets the three session state keys and reruns.

**`_generate_podcast()`:**
- Get the selected document name and output language from session state.
- Show a progress bar that updates through 4 stages: fetching chunks (10%), generating script (30%), synthesizing audio (60%), done (100%).
- Call `fetch_chunks_by_document`, then `generate_podcast_script`, then `synthesize_podcast`.
- Store results in `st.session_state.podcast_audio`, `podcast_timing`, `podcast_segments`.
- Call `st.rerun()` on success; show `st.error()` on exception.

**`_render_podcast_player()`:**
- Use `base64` to encode the WAV audio and `streamlit.components.v1.html` to embed a custom HTML player.
- Build transcript HTML: group timing entries by segment_index, create `<div class="segment">` elements containing `<span class="word" data-start="..." data-end="...">` elements for each word.
- The HTML player should include:
  - An `<audio>` element with the base64 WAV source.
  - Controls: Play/Pause button, Skip Back -10s, Skip Forward +10s, a speed selector (0.75x, 1x, 1.25x, 1.5x, 2x), and a time display.
  - A transcript container with max-height 500px and overflow scroll.
  - CSS: active words highlighted in yellow (#FFEB3B), spoken words dimmed (#666), active segment has light blue background (#f0f4ff).
  - JavaScript: on `timeupdate`, iterate all word spans, compare `currentTime * 1000` to each span's data-start/data-end attributes, toggle active/spoken classes. Auto-scroll to keep the active segment visible. On audio ended, reset the play button.
- Calculate player height based on number of segments: `min(700, 200 + num_segments * 80)`.

Make sure to import `generate_podcast_script` from `services.llm` and `synthesize_podcast` from `services.speech` in app.py.
```

---

## Tips for Using This Prompt

1. **Open the project** in VS Code with GitHub Copilot enabled.
2. **Open Copilot Chat** (click the Copilot icon or press `Ctrl+Shift+I`).
3. **Paste the entire prompt** from inside the code fence above.
4. Copilot will generate code for all three files. **Apply each suggestion** to the correct file:
   - `services/llm.py` — add the `generate_podcast_script` function at the bottom.
   - `services/speech.py` — add `synthesize_podcast` and `_assign_segments` at the bottom.
   - `app.py` — add session state init, the new tab, and the three helper functions.
5. **Verify imports** — make sure `app.py` imports `generate_podcast_script` and `synthesize_podcast`.
6. **Run the app** with `streamlit run app.py` and test the 🎙️ Podcasts tab.
