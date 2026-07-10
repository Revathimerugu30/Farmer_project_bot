"""
RAG (Retrieval-Augmented Generation) Pipeline
- Indexes documents (PDF, TXT) with chunking
- Stores embeddings using sentence-transformers + FAISS
- Retrieves top-k chunks for a query
"""
import os
import pickle
import logging
import hashlib
from pathlib import Path
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Optional heavy dependencies ────────────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

INDEX_DIR  = Path(__file__).parent.parent / "rag"
INDEX_FILE = INDEX_DIR / "faiss.index"
META_FILE  = INDEX_DIR / "metadata.pkl"
EMBED_MODEL = "all-MiniLM-L6-v2"

_embedder = None
_index    = None
_chunks: List[dict] = []


def _get_embedder():
    global _embedder
    if _embedder is None and _ST_AVAILABLE:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _save():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if _FAISS_AVAILABLE and _index is not None:
        faiss.write_index(_index, str(INDEX_FILE))
    with open(META_FILE, "wb") as f:
        pickle.dump(_chunks, f)


def _load():
    global _index, _chunks
    if META_FILE.exists():
        with open(META_FILE, "rb") as f:
            _chunks = pickle.load(f)
    if _FAISS_AVAILABLE and INDEX_FILE.exists():
        _index = faiss.read_index(str(INDEX_FILE))


# Load on import
_load()


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def _extract_text(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        if _PYMUPDF_AVAILABLE:
            doc = fitz.open(filepath)
            return "\n".join(page.get_text() for page in doc)
        else:
            return ""
    elif ext in {".txt", ".md"}:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def index_document(filepath: str, source_name: str = "") -> int:
    """Index a document file. Returns number of chunks added."""
    global _index, _chunks

    text = _extract_text(filepath)
    if not text.strip():
        logger.warning("No text extracted from %s", filepath)
        return 0

    from config import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP
    new_chunks = _chunk_text(text, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP)
    doc_id = hashlib.md5(filepath.encode()).hexdigest()[:8]

    embedder = _get_embedder()
    if embedder is None or not _FAISS_AVAILABLE:
        # Fallback: store chunks without embeddings (keyword search only)
        for i, chunk in enumerate(new_chunks):
            _chunks.append({"id": f"{doc_id}_{i}", "text": chunk, "source": source_name or filepath})
        _save()
        return len(new_chunks)

    vectors = embedder.encode(new_chunks, show_progress_bar=False).astype("float32")
    dim = vectors.shape[1]

    if _index is None:
        _index = faiss.IndexFlatL2(dim)

    _index.add(vectors)
    for i, chunk in enumerate(new_chunks):
        _chunks.append({"id": f"{doc_id}_{i}", "text": chunk, "source": source_name or filepath})

    _save()
    logger.info("Indexed %d chunks from %s", len(new_chunks), filepath)
    return len(new_chunks)


def search(query: str, top_k: int = 3) -> List[Tuple[str, str, float]]:
    """
    Search the RAG index.
    Returns list of (chunk_text, source, score).
    """
    if not _chunks:
        return []

    embedder = _get_embedder()

    # Semantic search with FAISS
    if embedder is not None and _FAISS_AVAILABLE and _index is not None and _index.ntotal > 0:
        q_vec = embedder.encode([query]).astype("float32")
        k = min(top_k, _index.ntotal)
        distances, indices = _index.search(q_vec, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(_chunks):
                chunk = _chunks[idx]
                results.append((chunk["text"], chunk["source"], float(dist)))
        return results

    # Fallback: simple keyword search
    query_words = set(query.lower().split())
    scored = []
    for chunk in _chunks:
        chunk_words = set(chunk["text"].lower().split())
        score = len(query_words & chunk_words) / max(len(query_words), 1)
        scored.append((chunk["text"], chunk["source"], score))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]


def get_context_for_query(query: str, top_k: int = 3) -> str:
    """Return a formatted context string for inclusion in the AI prompt."""
    results = search(query, top_k)
    if not results:
        return ""
    parts = []
    for text, source, _ in results:
        parts.append(f"[Source: {source}]\n{text}")
    return "\n\n---\n\n".join(parts)


def list_documents() -> List[dict]:
    """Return unique document sources in the index."""
    seen, docs = set(), []
    for chunk in _chunks:
        src = chunk.get("source", "unknown")
        if src not in seen:
            seen.add(src)
            docs.append({"source": src, "chunks": sum(1 for c in _chunks if c.get("source") == src)})
    return docs


def delete_all() -> None:
    """Clear the entire index."""
    global _index, _chunks
    _index  = None
    _chunks = []
    _save()
