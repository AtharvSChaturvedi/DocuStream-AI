# DocuStream — Research Paper RAG Assistant

Upload academic papers as PDFs, ask questions in plain English, and get
answers grounded in the papers — with every claim cited back to a source
title and page number.

## Why this architecture

| Piece | Choice | Why |
|---|---|---|
| Embeddings | Gemini `text-embedding-004` | Free tier, strong quality, separate `retrieval_document` / `retrieval_query` task types improve retrieval accuracy |
| Vector store | Chroma Cloud | Managed, persistent, metadata filtering (search one paper or all of them) |
| Generation | Groq (Llama 3.3 70B) | Very low latency — matters for a live demo in an interview |
| Backend | Flask REST API | Matches your existing stack (Campus-Navigator, ElectroVerse) |
| Deploy | Vercel serverless | Free, matches your ElectroVerse deployment experience |

## How it works

1. **Ingest**: PDF → text extracted per page → chunked (900 chars, 150 overlap,
   page number preserved) → each chunk embedded → stored in Chroma with
   `{paper_id, title, page}` metadata.
2. **Query**: question embedded → top-5 most similar chunks retrieved from
   Chroma (optionally scoped to one paper) → chunks + question sent to Groq
   with a system prompt that forces citation and forbids answering outside
   the retrieved context.
3. **Answer**: returned with inline `[1] [2]` markers and a "Works cited"
   list of paper + page.

## Project structure

```
research-rag/
├── api/index.py        # Flask app + routes (Vercel entrypoint)
├── app/
│   ├── embeddings.py    # Gemini embedding calls
│   ├── chroma_client.py # Chroma Cloud connection
│   ├── pdf_utils.py     # PDF parsing + chunking
│   └── rag.py           # ingest / retrieve / generate pipeline
├── templates/index.html
├── static/style.css, script.js
├── requirements.txt
├── vercel.json
└── .env.example
```

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # fill in your keys
python api/index.py             # http://localhost:5000
```

## Deploy to Vercel

```bash
npm i -g vercel
vercel login
vercel
```

Then in the Vercel dashboard, add the same environment variables from
`.env` under **Project → Settings → Environment Variables**, and redeploy:

```bash
vercel --prod
```

## Extending it (good "what would you add next" answers for interviews)

- **Reranking**: add a cross-encoder rerank step after Chroma's top-k to
  push precision higher before generation.
- **Hybrid search**: combine Chroma's vector search with BM25 keyword
  search for queries with exact terms (equation names, author names).
- **Evaluation**: log retrieved-chunk relevance and answer faithfulness
  against a small hand-labeled Q&A set (RAGAS-style) to quantify quality.
- **Streaming**: switch the Groq call to streaming and pipe tokens to the
  frontend for a faster perceived response.
- **Multi-paper synthesis**: prompt the model to compare/contrast claims
  across papers when a question spans more than one source.

## Resume line

> **DocuStream — Research Paper RAG Assistant** — Python, Flask, Chroma,
> Gemini, Groq
> Built a retrieval-augmented QA system over uploaded academic papers with
> page-level citation grounding; used Gemini embeddings for semantic
> search over Chroma Cloud and Groq-hosted Llama 3.3 for low-latency,
> context-constrained generation. Deployed on Vercel.
# DocuStream-AI
