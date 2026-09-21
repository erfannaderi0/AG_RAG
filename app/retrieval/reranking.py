# app/retrieval/reranking.py
"""
Reranks a list of Documents (typically fusion.py's RRF output) against the
original query using a local cross-encoder, for a final precision pass
before the top results go to generation.
"""

import logging
import sys
from pathlib import Path

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from app.config import settings

logger = logging.getLogger(__name__)

_reranker = None


def _get_reranker() -> CrossEncoder:
    """Lazily instantiate the cross-encoder once, reused across calls."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(settings.reranker_model_name)
    return _reranker


def rerank(query: str, documents: list[Document], top_n: int = 5) -> list[Document]:
    """
    Score each (query, chunk_text) pair with a cross-encoder and return the
    top_n documents sorted by that score, descending.
    """
    if not documents:
        return []

    model = _get_reranker()
    pairs = [(query, doc.page_content) for doc in documents]
    scores = model.predict(pairs)

    for doc, score in zip(documents, scores):
        doc.metadata["rerank_score"] = float(score)

    ranked = sorted(documents, key=lambda d: d.metadata["rerank_score"], reverse=True)

    logger.info(
        "rerank: scored %d document(s), returning top %d", len(documents), min(top_n, len(ranked))
    )

    return ranked[:top_n]


if __name__ == "__main__":
    from app.retrieval.bm25 import bm25_search
    from app.retrieval.fusion import reciprocal_rank_fusion
    from app.retrieval.vector import similarity_search

    logging.basicConfig(level=logging.INFO)

    query = "business expense meals"
    fused = reciprocal_rank_fusion(similarity_search(query), bm25_search(query))
    results = rerank(query, fused)
    for doc in results:
        print(doc.metadata, doc.page_content[:80])
