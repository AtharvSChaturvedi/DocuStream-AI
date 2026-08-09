"""
Core RAG pipeline for the research-paper assistant.

Every function now takes an `owner_id` - a random ID assigned per browser
session (see api/index.py). Documents are tagged with it on upload and
every read is filtered by it, so different visitors never see each
other's papers even though they share one Chroma collection.

Flow:
  ingest_pdf()      PDF bytes -> pages -> chunks -> Gemini embeddings -> Chroma
  answer_question()  question -> Gemini query embedding -> Chroma top-k ->
                      Groq generation grounded in retrieved excerpts
"""
import os
import uuid
from groq import Groq

from app.embeddings import embed_texts, embed_query
from app.chroma_client import get_collection
from app.pdf_utils import extract_pages, chunk_pages

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = (
    "You are a careful research assistant. Answer the user's question using "
    "ONLY the numbered excerpts provided below, which come from uploaded "
    "academic papers. Cite every claim with the matching bracket number, "
    "e.g. [1] or [2][3]. If the excerpts don't contain enough information "
    "to answer, say so plainly instead of guessing or using outside "
    "knowledge."
)


def ingest_pdf(file_bytes, filename, owner_id):
    """Parses a PDF, embeds its chunks, and stores them in Chroma, tagged
    with owner_id so only this visitor can retrieve them later."""
    pages = extract_pages(file_bytes)
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError(
            "No extractable text found in this PDF. It may be scanned "
            "images rather than selectable text."
        )

    paper_id = str(uuid.uuid4())[:8]
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    ids = [f"{paper_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "paper_id": paper_id,
            "title": filename,
            "page": c["page"],
            "owner_id": owner_id,
        }
        for c in chunks
    ]

    collection = get_collection()
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return {"paper_id": paper_id, "title": filename, "chunks": len(chunks)}


def list_papers(owner_id):
    """Returns the distinct set of papers this owner has uploaded."""
    collection = get_collection()
    data = collection.get(where={"owner_id": owner_id}, include=["metadatas"])
    seen = {}
    for meta in data.get("metadatas", []):
        pid = meta.get("paper_id")
        if pid and pid not in seen:
            seen[pid] = meta.get("title")
    return [{"paper_id": pid, "title": title} for pid, title in seen.items()]


def delete_paper(owner_id, paper_id):
    """Removes all chunks belonging to one paper, scoped to this owner
    so you can't delete someone else's document even by guessing an id."""
    collection = get_collection()
    collection.delete(
        where={"$and": [{"owner_id": owner_id}, {"paper_id": paper_id}]}
    )


def answer_question(question, owner_id, top_k=5, paper_id=None):
    """Retrieves relevant chunks (scoped to this owner) and asks Groq to
    answer, grounded and cited."""
    collection = get_collection()
    query_embedding = embed_query(question)

    if paper_id:
        where = {"$and": [{"owner_id": owner_id}, {"paper_id": paper_id}]}
    else:
        where = {"owner_id": owner_id}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return {
            "answer": (
                "There's nothing to search yet - upload a paper first, "
                "then ask again."
            ),
            "sources": [],
        }

    context_blocks = [
        f"[{i + 1}] (Source: {meta.get('title')}, page {meta.get('page')})\n{doc}"
        for i, (doc, meta) in enumerate(zip(docs, metas))
    ]
    context = "\n\n".join(context_blocks)
    user_prompt = f"Excerpts:\n{context}\n\nQuestion: {question}"

    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    answer = completion.choices[0].message.content

    sources = [
        {"title": meta.get("title"), "page": meta.get("page")} for meta in metas
    ]
    return {"answer": answer, "sources": sources}
