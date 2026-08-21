# DocuStream AI

Upload research papers as PDFs, ask questions in plain English, and get answers grounded in the papers — with every claim cited back to a source title and exact page number. Also scores each paper against real reviewer criteria with a transparent Readiness Score.

Built as a full retrieval-augmented generation (RAG) pipeline: PDF parsing → chunking → embeddings → vector search → grounded generation, wired end-to-end with a live UI and no external framework doing the RAG logic for you.

## Live demo

`https://docu-stream-ai-gold.vercel.app/`

Each device gets its own private, isolated space — papers you upload aren't visible to anyone else, and persist until you remove them (no re-uploading every visit).

## How it works

### Ask questions about a paper

1. **Ingest** — a PDF is parsed page-by-page, split into overlapping ~900-character chunks (page number preserved on every chunk), and each chunk is embedded with Gemini's `gemini-embedding-001` model, then stored in Chroma Cloud tagged with a per-device owner ID.
2. **Retrieve** — a question is embedded the same way and matched against the top-5 most similar chunks in Chroma, scoped to that device's own papers (and optionally to a single chosen paper).
3. **Generate** — the retrieved excerpts and the question are sent to Groq (`openai/gpt-oss-120b`) with a system prompt that forces citation and forbids answering outside the retrieved context.
4. **Answer** — returned with inline `[1] [2]` markers and a "Works cited" list of paper + page, so every claim is traceable to its source, typed out live rather than appearing all at once.

### Check a paper's Readiness Score

1. The full paper (all chunks, reassembled in original order — not just the top-k relevant ones) is sent to Groq, prompted to act as an experienced reviewer.
2. It scores the paper 0-10 against 7 real review criteria: structure & formatting, novelty & contribution, methodology rigor, related-work grounding, clarity & writing, results & evaluation, and citation practices — with a short justification for each.
3. The 7 scores are summed and converted to a transparent percentage (`sum / 70 × 100`) — computed in code, not asked of the model directly, so the number is always explainable.
4. **This is a heuristic estimate against common review criteria, not a validated predictor of acceptance** — no public dataset of paper accept/reject outcomes exists for most venues (rejected papers are typically never published anywhere), so there's nothing to train or calibrate a true prediction model against. The UI states this directly rather than implying a guarantee.

## Why these tools

| Piece | Choice | Why |
|---|---|---|
| Embeddings | Gemini `gemini-embedding-001` | Free tier, strong retrieval quality, separate query/document embedding modes |
| Vector store | Chroma Cloud | Managed, persistent, metadata filtering for per-device and per-paper scoping |
| Generation | Groq (`openai/gpt-oss-120b`) | Very low latency — matters for a responsive, demo-able chat experience |
| Backend | Flask REST API | Simple, explicit, easy to reason about every request |
| Deploy | Vercel serverless | Free, zero-maintenance hosting |

## Features

- Upload multiple PDFs and scope questions to one paper or search across all of them
- Inline citations tied to exact source + page number, not just "somewhere in this paper"
- Readiness Score — scores an uploaded paper against real reviewer criteria (structure, novelty, methodology, related work, clarity, evaluation, citations), with a transparent percentage and specific feedback per category
- Per-device privacy — no accounts needed, but no visitor sees another visitor's documents; persists across visits rather than resetting each session
- One-click removal of any uploaded paper
- Live, typed answer reveal instead of the response appearing all at once
- Clean, distinct UI (not a generic chat-bubble template)

## Project structure

```
docustream-ai/
├── api/index.py         # Flask app + routes (Vercel entrypoint)
├── app/
│   ├── embeddings.py     # Gemini embedding calls
│   ├── chroma_client.py  # Chroma Cloud connection
│   ├── pdf_utils.py      # PDF parsing + chunking
│   |── rag.py            # ingest / retrieve / generate / delete pipeline
|   └── readiness.py      # Readiness Score analysis
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
- **True token streaming** — stream Groq's response as it's generated, instead of animating a client-side reveal after the full response arrives
- **Multi-paper synthesis** — prompt the model to explicitly compare/contrast claims when a question spans more than one source
- **General publishing-probability estimation** — extending the Readiness Score beyond a criteria-based heuristic toward a broader, venue-agnostic estimate of publication readiness, once a defensible basis for calibrating it (e.g. published research on venues with open review data such as PeerRead or OpenReview) is incorporated

## Tech stack

Python · Flask · Chroma Cloud · Google Gemini (embeddings) · Groq (`gpt-oss-120b`) · Vercel
