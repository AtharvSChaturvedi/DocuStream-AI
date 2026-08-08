"""
Lazily-initialized Chroma Cloud client. Lazy init matters on serverless
platforms (Vercel) - we don't want to open a connection at import time,
only when a request actually needs it.
"""
import os
import chromadb

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.CloudClient(
        api_key=os.environ["CHROMA_API_KEY"],
        tenant=os.environ["CHROMA_TENANT"],
        database=os.environ["CHROMA_DATABASE"],
    )
    _collection = _client.get_or_create_collection(
        name=os.environ.get("CHROMA_COLLECTION", "rag-docs")
    )
    return _collection
