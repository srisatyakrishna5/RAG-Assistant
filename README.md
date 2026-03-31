# 📄 RAG Document Assistant

A **Streamlit-based Retrieval Augmented Generation (RAG)** application that lets you upload PDF documents, index them into Azure AI Search, and have an intelligent conversation with their contents — complete with page-level citations, multilingual responses, voice input, and text-to-speech output.

All AI processing is powered by **Azure OpenAI (GPT-4.1)** and **Azure Cognitive Services**, meaning no data is sent to any third-party system outside your own Azure subscription.

---

## Table of Contents

1. [What the App Does](#1-what-the-app-does)
2. [Architecture Overview](#2-architecture-overview)
3. [Feature Details](#3-feature-details)
4. [Project Structure](#4-project-structure)
5. [Azure Services Used](#5-azure-services-used)
6. [Prerequisites](#6-prerequisites)
7. [Setup & Installation](#7-setup--installation)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [Using the Application](#9-using-the-application)
10. [How RAG Works (Plain English)](#10-how-rag-works-plain-english)
11. [Supported Languages](#11-supported-languages)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What the App Does

Imagine being able to upload a 200-page technical report and immediately ask it questions like:

- *"What are the key findings on page 47?"*
- *"Summarise the risk mitigation strategies mentioned in this document."*
- *"What does the report say about budget projections?"*

Instead of reading the whole document, the app finds the most relevant passages and uses GPT-4.1 to give you a direct, cited answer in seconds.  You can also receive answers spoken aloud in your chosen language, and ask questions by voice.

---

## 2. Architecture Overview

### Document Ingestion Pipeline (one-time per document)

```
┌──────────┐     ┌──────────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Upload  │────▶│ Document Intelligence │────▶│ Chunk + Embed   │────▶│  AI Search   │
│   PDF    │     │  (Layout Analysis)    │     │ (OpenAI Ada-002) │     │  (Index)     │
└──────────┘     └──────────────────────┘     └─────────────────┘     └──────┬───────┘
                                                                              │
                      Extracts text            Splits into 1000-char         Stores text +
                      from every page          overlapping chunks +           vector embeddings
                      preserving layout        generates float vectors        for hybrid search
```

### Question Answering Pipeline (every user question)

```
┌──────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Answer  │◀────│   GPT-4.1 Synthesis  │◀────│  Hybrid Search   │◀──── User Question
│ + Cites  │     │  (with citations)    │     │ (BM25 + Vector)  │
└────┬─────┘     └──────────────────────┘     └──────────────────┘
     │
     ├──▶  Azure Translator (optional, for non-English output)
     └──▶  Azure Speech TTS (optional, for spoken playback)
```

---

## 3. Feature Details

### 📤 PDF Upload & Indexing
- Drag-and-drop or browse to upload any PDF file.
- Azure Document Intelligence's **prebuilt-layout** model extracts text per page, handling complex layouts, tables, and multi-column text.
- Text is split into **1 000-character overlapping chunks** (200-char overlap) to ensure no context is lost at chunk boundaries.
- Each chunk is embedded into a **3 072-dimensional float vector** using Azure OpenAI's `text-embedding-ada-002` model.
- Both the raw text and the vector are stored in an **Azure AI Search** index, enabling combined full-text and semantic retrieval.

### 💬 Conversational Chat (Q&A)
- Multi-turn chat interface (full conversation history preserved in the session).
- Each question triggers a **hybrid search** combining:
  - **BM25 full-text search** — finds chunks containing the exact or similar keywords.
  - **HNSW vector (semantic) search** — finds chunks that are semantically similar even if different words are used.
  - Azure AI Search merges both result sets using **Reciprocal Rank Fusion (RRF)** to produce a single ranked list.
- Top 5 most relevant chunks are passed to GPT-4.1 as grounding context.
- GPT-4.1 generates an answer with **inline source citations** (e.g., `[Source 2 - Page 7]`).
- Each assistant reply includes a collapsible **"Sources & Citations"** panel showing the exact text excerpts and relevance scores.

### 📝 Document Summary
- Select any indexed document from the Summary tab dropdown.
- The app fetches **all chunks** for that document in reading order and passes them to GPT-4.1 for a comprehensive, structured summary.
- Summaries include bullet points and page-number references.
- Summaries can be generated in any supported language.

### 🎤 Voice Input (Speech-to-Text)
- Click the microphone button, speak your question, then click stop.
- The audio is transcribed using **Azure Speech Service** (English recognition).
- The transcribed text is shown on-screen before being submitted as the query.
- Requires the `azure-cognitiveservices-speech` SDK and Azure Speech credentials.

### 🔊 Text-to-Speech (spoken answers)
- After each answer is generated, a condensed spoken version is synthesized using **Azure Neural TTS**.
- The spoken version is reformatted by GPT-4.1 to remove markdown, bullet points, and citation markers, producing natural-sounding prose.
- Audio plays automatically in the browser and is also saved in the chat history.
- Voices are language-specific (see [Supported Languages](#11-supported-languages)).
- The TTS toggle in the sidebar lets users turn spoken playback on or off at any time.

### 🌐 Multilingual Output
- All AI-generated text (answers AND spoken summaries) can be translated to Hindi, French, or Telugu using the **Azure Translator** service.
- Select the desired language from the sidebar before asking a question.
- If `AZURE_TRANSLATOR_KEY` is not configured, the app continues to work in English.

---

## 4. Project Structure

```
document-advisor/
│
├── app.py                        # Main Streamlit app — UI rendering and event handling
├── config.py                     # Centralised configuration via environment variables
├── requirements.txt              # Python package dependencies
├── README.md                     # This file
├── PROMPTS.md                    # AI prompts used to generate this codebase
│
└── services/                     # Backend service modules (no Streamlit dependency)
    ├── __init__.py
    ├── document_intelligence.py  # PDF → per-page text (Azure Document Intelligence)
    ├── chunker.py                # Per-page text → overlapping chunks
    ├── embeddings.py             # Text chunks → float vectors (Azure OpenAI ada-002)
    ├── search_index.py           # Index schema management + chunk upload (Azure AI Search)
    ├── search.py                 # Hybrid search, document name list, chunk fetch
    ├── llm.py                    # Answer generation, speech summary, doc summary (GPT-4.1)
    ├── speech.py                 # Speech-to-Text + Text-to-Speech (Azure Speech)
    └── translation.py            # Text translation (Azure Translator)
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit UI, session state, user interaction, pipeline orchestration |
| `config.py` | Load `.env` file; expose all credentials as named constants |
| `document_intelligence.py` | Call Azure Document Intelligence prebuilt-layout model |
| `chunker.py` | Sliding-window character chunking with overlap |
| `embeddings.py` | Batch embedding generation via Azure OpenAI |
| `search_index.py` | Create/verify AI Search index schema; upload embedded chunks |
| `search.py` | Hybrid BM25+vector search; list document names; fetch all chunks |
| `llm.py` | GPT-4.1 prompting for Q&A answers, spoken summaries, doc summaries |
| `speech.py` | WAV transcription (STT) and neural TTS synthesis |
| `translation.py` | Post-generation translation for non-English output |

---

## 5. Azure Services Used

| Service | Purpose | Required? |
|---|---|---|
| **Azure Document Intelligence** | Extract text from uploaded PDFs | ✅ Yes |
| **Azure AI Search** | Store and retrieve document chunks (full-text + vector) | ✅ Yes |
| **Azure OpenAI — GPT-4.1** | Generate answers and document summaries | ✅ Yes |
| **Azure OpenAI — text-embedding-ada-002** | Convert text chunks to semantic vectors | ✅ Yes |
| **Azure Speech Service** | Voice input (STT) and voice output (TTS) | ⚙️ Optional |
| **Azure Translator** | Translate answers to non-English languages | ⚙️ Optional |

---

## 6. Prerequisites

Before setting up the application, make sure you have:

- **Python 3.10 or higher** installed on your machine.
- An **Azure subscription** (a free trial works for testing).
- The following Azure resources provisioned:
  - Azure Document Intelligence (any tier — Free F0 works for small documents)
  - Azure AI Search (Free tier or Basic)
  - Azure OpenAI with two model deployments:
    - A **GPT-4.1** (or GPT-4) deployment for chat completions
    - A **text-embedding-ada-002** deployment for embeddings
- *(Optional)* Azure Speech Service resource — for voice input/output
- *(Optional)* Azure Translator resource — for multilingual responses

---

## 7. Setup & Installation

### Step 1 — Clone or download the project

```bash
git clone <repository-url>
cd document-advisor
```

### Step 2 — Create a Python virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The `azure-cognitiveservices-speech` package includes a native binary.
> If it fails to install on your platform, the app will still work — voice features
> will simply be disabled.

### Step 4 — Configure environment variables

Create a file named `.env` in the project root (same folder as `app.py`) with the following content, replacing the placeholder values with your actual Azure credentials:

```dotenv
# ── Azure Document Intelligence ──────────────────────────────────
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=<your-key>

# ── Azure AI Search ───────────────────────────────────────────────
AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_KEY=<your-admin-key>
AZURE_SEARCH_INDEX_NAME=rag-documents

# ── Azure OpenAI ──────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2025-03-01-preview

# ── Azure Speech (optional) ───────────────────────────────────────
AZURE_SPEECH_KEY=<your-key>
AZURE_SPEECH_REGION=eastus

# ── Azure Translator (optional) ───────────────────────────────────
AZURE_TRANSLATOR_KEY=<your-key>
AZURE_TRANSLATOR_REGION=global
```

> **Security tip:** Never commit your `.env` file to version control.  Add it to `.gitignore`.

### Step 5 — Launch the application

```bash
streamlit run app.py
```

Streamlit will print a local URL (typically `http://localhost:8501`).  Open it in your browser.

---

## 8. Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|---|---|---|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Full HTTPS endpoint URL of your Document Intelligence resource | `https://mydi.cognitiveservices.azure.com/` |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | API key from the Azure Portal (Keys and Endpoint blade) | `abc123...` |
| `AZURE_SEARCH_ENDPOINT` | Full HTTPS endpoint URL of your AI Search service | `https://mysearch.search.windows.net` |
| `AZURE_SEARCH_KEY` | Admin key from the Azure Portal (Keys blade) | `xyz789...` |
| `AZURE_OPENAI_ENDPOINT` | Full HTTPS endpoint URL of your Azure OpenAI resource | `https://myoai.openai.azure.com/` |
| `AZURE_OPENAI_KEY` | API key from the Azure Portal | `key123...` |

### Optional / Defaulted Variables

| Variable | Default | Description |
|---|---|---|
| `AZURE_SEARCH_INDEX_NAME` | `rag-documents` | Name of the search index to create/use |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1` | Name of your GPT-4 chat deployment |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-ada-002` | Name of your embedding model deployment |
| `AZURE_OPENAI_API_VERSION` | `2025-03-01-preview` | Azure OpenAI REST API version |
| `AZURE_SPEECH_KEY` | *(empty)* | Speech Service API key — leave blank to disable voice |
| `AZURE_SPEECH_REGION` | *(empty)* | Speech Service region (e.g., `eastus`) |
| `AZURE_TRANSLATOR_KEY` | *(empty)* | Translator API key — leave blank to disable translation |
| `AZURE_TRANSLATOR_REGION` | *(empty)* | Translator region (e.g., `global`) |

---

## 9. Using the Application

### Uploading a Document

1. Open the app at `http://localhost:8501`.
2. In the **left sidebar**, scroll down to **"➕ Upload New Document"**.
3. Click **"Browse files"** and select a PDF from your computer.
4. Click **"🚀 Analyze & Index"**.
5. Watch the progress bar as the app:
   - Extracts text from every page using Document Intelligence.
   - Previews the first 3 pages of extracted text in an expandable panel.
   - Splits the text into overlapping chunks.
   - Creates the Azure AI Search index (first run only).
   - Generates vector embeddings and uploads everything to the index.
6. When the green "🎉 Indexed successfully!" banner appears, the document is ready.

### Asking Questions (Chat Tab)

1. Click the **"💬 Chat"** tab (visible by default).
2. Type your question in the **"Ask a question about your documents…"** input box at the bottom and press Enter.
3. The assistant will:
   - Search the index for the 5 most relevant passages.
   - Generate a cited answer using GPT-4.1.
   - Display the answer with a "📚 Sources & Citations" panel showing which pages it referenced.
   - (If TTS is enabled) Automatically play a spoken summary.
4. Continue asking follow-up questions — the full conversation history is preserved.

### Voice Input

1. Make sure **AZURE_SPEECH_KEY** and **AZURE_SPEECH_REGION** are set in `.env`.
2. In the Chat tab, click the **microphone** icon.
3. Speak your question clearly and then click **stop**.
4. The app will display the transcribed text (e.g., "🗣️ Heard: What is the conclusion?") and submit it automatically.

### Generating a Document Summary

1. Click the **"📝 Summary"** tab.
2. Select a document from the dropdown.
3. Click **"📝 Generate Summary"**.
4. The app fetches all chunks of that document and produces a structured multi-page summary with page citations.
5. Click "🗑️ Clear summary" to remove it.

### Changing the Output Language

1. In the sidebar, locate **"🌐 Output Language"**.
2. Select **English**, **Hindi**, **French**, or **Telugu**.
3. All subsequent answers and summaries will be translated into the chosen language.
4. Voice output (TTS) will also switch to the Neural voice for that language.

---

## 10. How RAG Works (Plain English)

Traditional search returns links to documents.  RAG goes further — it reads the relevant passages *for* you and composes a direct answer.

**Step 1 — Indexing (done once per document)**

The PDF is broken into small text windows (chunks).  Each chunk is converted into a mathematical "fingerprint" (embedding vector) that captures its meaning.  Both the text and the fingerprint are stored in Azure AI Search.

**Step 2 — Retrieval (done for every question)**

When you ask a question, the app creates a fingerprint of your question and searches the index for chunks whose fingerprints are closest (semantically similar), plus chunks that share keywords with your question.  The two lists are merged and the top 5 results are selected.

**Step 3 — Generation (done for every question)**

The top 5 chunks, along with your question, are sent to GPT-4.1 with a prompt that says: *"Answer this question using ONLY the provided document excerpts, and cite your sources."*  GPT-4.1 reads the context and writes an answer — it cannot make things up because it is constrained to the provided text.

This is fundamentally different from asking GPT-4.1 a question directly (without RAG), where it relies on training data that may be outdated or wrong.

---

## 11. Supported Languages

| Language | TTS Voice | Translator Code |
|---|---|---|
| English  | `en-US-JennyNeural`  | `en` |
| Hindi    | `hi-IN-SwaraNeural`  | `hi` |
| French   | `fr-FR-DeniseNeural` | `fr` |
| Telugu   | `te-IN-ShrutiNeural` | `te` |

To add more languages, extend the `LANGUAGE_CONFIG` dictionary in `config.py` with the appropriate Azure Translator language code and Azure Neural TTS voice name.

---

## 12. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| "⚠️ Missing Azure configuration" error on startup | One or more required environment variables are not set in `.env` | Check `.env` exists in the project root and all required variables are filled in |
| "Document Intelligence error" on upload | Invalid endpoint/key, or the PDF is corrupt/password-protected | Verify credentials in Azure Portal; try a different PDF |
| "Indexing error" on upload | AI Search quota exceeded or key has read-only permissions | Use an **Admin** key (not a Query key); check your Search tier limits |
| "Could not understand the audio" | Background noise or microphone quality | Speak closer to the microphone; try in a quiet environment |
| "Azure Translator connected" not shown | `AZURE_TRANSLATOR_KEY` missing from `.env` | Add the key; answers will remain in English otherwise |
| Voice features show as "disabled" | Speech SDK missing or credentials absent | Run `pip install azure-cognitiveservices-speech`; add Speech key/region to `.env` |
| Answers are slow | Normal — GPT-4.1 typically takes 3–10 seconds | Expected behaviour; no action needed |
| Old documents re-appear after clearing chat | Search index is persistent (by design) | Use the Azure Portal to delete the index manually if a full reset is needed |

