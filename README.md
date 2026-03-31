# 📄 RAG Document Assistant

A Streamlit-based RAG (Retrieval Augmented Generation) prototype that lets you upload a PDF, analyze it with Azure Document Intelligence, index it into Azure AI Search, and interact with it via GPT-4.1.

## Architecture

```
┌──────────┐     ┌─────────────────────┐     ┌────────────────┐     ┌──────────────┐
│  Upload   │────▶│ Document Intelligence│────▶│  Chunk + Embed │────▶│  AI Search   │
│   PDF     │     │  (Layout Analysis)   │     │  (OpenAI Ada)  │     │  (Index)     │
└──────────┘     └─────────────────────┘     └────────────────┘     └──────┬───────┘
                                                                           │
┌──────────┐     ┌─────────────────────┐     ┌────────────────┐           │
│  Answer   │◀───│  GPT-4.1 Synthesis  │◀───│ Hybrid Search  │◀──────────┘
│ + Cites   │     │  (with citations)   │     │ (text+vector)  │
└──────────┘     └─────────────────────┘     └────────────────┘
```

## Prerequisites

- Python 3.10+
- Azure Document Intelligence resource
- Azure AI Search resource
- Azure OpenAI resource with **GPT-4.1** and **text-embedding-ada-002** deployments

## Setup

1. **Create a virtual environment** (if not already present):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # Linux/macOS
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**: Copy the template and fill in your values:
   ```bash
   copy .env.template .env   # Windows
   # cp .env.template .env   # Linux/macOS
   ```
   Then edit `.env` with your Azure resource endpoints and keys.

4. **Run the app**:
   ```bash
   streamlit run app.py
   ```

## Environment Variables

| Variable | Description |
|---|---|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Document Intelligence resource endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Document Intelligence API key |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search service endpoint |
| `AZURE_SEARCH_KEY` | Azure AI Search admin key |
| `AZURE_SEARCH_INDEX_NAME` | Search index name (default: `rag-documents`) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | GPT-4.1 deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment name |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version |

## Usage

1. **Upload** — Select a PDF file and click "Analyze & Index Document"
2. **Wait** — The app extracts text via Document Intelligence, chunks it, generates embeddings, and uploads to AI Search
3. **Ask** — Use the chat interface to ask questions; answers include page-level citations
