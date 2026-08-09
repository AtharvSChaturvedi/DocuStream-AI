# DocuStream AI

Upload research papers as PDFs, ask questions in plain English, and get answers grounded in the papers — with every claim cited back to a source title and exact page number.

Built as a full retrieval-augmented generation (RAG) pipeline: PDF parsing → chunking → embeddings → vector search → grounded generation, wired end-to-end with a live UI and no external framework doing the RAG logic for you.

## Live demo

`<add your Vercel URL here>`

Each browser session gets its own private, isolated space — papers you upload aren't visible to anyone else, and you can remove any paper you've added at any time.

## How it works

1. **Ingest** — a PDF is parsed page-by-page, split into overlapping ~900-character chunks (page number preserved on every chunk), and each chunk is embedded with Gemini's `gemini-embedding-001` model, then stored in Chroma Cloud tagged with a per-session owner ID.
2. **Retrieve** — a question is embedded the same way and matched against the top-5 most similar chunks in Chroma, scoped to that session's own papers (and optionally to a single chosen paper).
3. **Generate** — the retrieved excerpts and the question are sent to Groq (Llama 3.3 70B) with a system prompt that forces citation and forbids answering outside the retrieved context.
4. **Answer** — returned with inline `[1] [2]` markers and a "Works cited" list of paper + page, so every claim is traceable to its source.

## Why these tools

| Piece | Choice | Why |
|---|---|---|
| Embeddings | Gemini `gemini-embedding-001` | Free tier, strong retrieval quality, separate query/document embedding modes |
| Vector store | Chroma Cloud | Managed, persistent, metadata filtering for per-session and per-paper scoping |
| Generation | Groq (Llama 3.3 70B) | Very low latency — matters for a responsive, demo-able chat experience |
| Backend | Flask REST API | Simple, explicit, easy to reason about every request |
| Deploy | Vercel serverless | Free, zero-maintenance hosting |

## Features

- Upload multiple PDFs and scope questions to one paper or search across all of them
- Inline citations tied to exact source + page number, not just "somewhere in this paper"
- Per-session privacy — no accounts needed, but no visitor sees another visitor's documents
- One-click removal of any uploaded paper
- Clean, distinct UI (not a generic chat-bubble template)

## Project structure

```
docustream-ai/
├── api/index.py         # Flask app + routes (Vercel entrypoint)
├── app/
│   ├── embeddings.py     # Gemini embedding calls
│   ├── chroma_client.py  # Chroma Cloud connection
│   ├── pdf_utils.py      # PDF parsing + chunking
│   └── rag.py            # ingest / retrieve / generate / delete pipeline
├── templates/index.html
├── static/style.css, script.js
├── requirements.txt
├── vercel.json
└── .env.example
```

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env            # fill in your real keys
python api/index.py             # http://localhost:5000
```

## Deploy to Vercel

Connect the GitHub repo in the Vercel dashboard, add the same environment variables from `.env` under **Project → Settings → Environment Variables**, and deploy. `vercel.json` handles the routing.

## What I'd add next

- **Reranking** — a cross-encoder rerank step after Chroma's top-k, to push precision higher before generation
- **Hybrid search** — combine vector search with BM25 keyword search for queries with exact terms (equations, author names)
- **Evaluation** — a small hand-labeled Q&A set scored for retrieval relevance and answer faithfulness (RAGAS-style)
- **Streaming** — stream Groq's response token-by-token instead of waiting for the full answer
- **Multi-paper synthesis** — prompt the model to explicitly compare/contrast claims when a question spans more than one source

## Tech stack

Python · Flask · Chroma Cloud · Google Gemini (embeddings) · Groq (Llama 3.3) · Vercel
