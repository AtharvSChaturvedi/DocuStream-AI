"""
Thin wrapper around Gemini's embedding model.

Uses the current `google-genai` SDK and the `gemini-embedding-001` model.
(The older `google-generativeai` package and `text-embedding-004` model
are both retired as of early 2026 - see README note.)

We use Gemini here (not Groq) because Groq doesn't serve an embeddings
endpoint - Groq is used later purely for fast generation.
"""
import os
from google import genai
from google.genai.types import EmbedContentConfig

_client = None

EMBED_MODEL = "gemini-embedding-001"
# 768 keeps vectors compact while staying in Google's recommended
# high-quality range (768 / 1536 / 3072). Change here if you want more
# precision at the cost of storage/latency - just re-ingest existing
# papers afterward, since old and new vectors won't be comparable.
OUTPUT_DIMENSIONALITY = 768
BATCH_SIZE = 90  # stay under the API's per-call batch limit


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def embed_texts(texts, task_type="RETRIEVAL_DOCUMENT"):
    """Embed a list of strings for storage. Returns a list of vectors."""
    client = _get_client()
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=batch,
            config=EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=OUTPUT_DIMENSIONALITY,
            ),
        )
        all_embeddings.extend(e.values for e in result.embeddings)
    return all_embeddings


def embed_query(text):
    """Embed a single query string. Uses a different task_type than
    document embedding, which noticeably improves retrieval quality."""
    client = _get_client()
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=OUTPUT_DIMENSIONALITY,
        ),
    )
    return result.embeddings[0].values