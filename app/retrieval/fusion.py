# app/retrieval/fusion.py
"""
Merges the vector-search and BM25 ranked lists into one ranked list using
Reciprocal Rank Fusion (RRF). Each list contributes 1/(k + rank) per chunk;
scores are summed across lists by chunk id, then sorted descending.
"""

import logging

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    vector_results: list[Document],
    bm25_results: list[Document],
    k: int = 60,
    top_n: int = 10,
) -> list[Document]:
    """
    Fuse two ranked Document lists into one, using each result's chunk id
    (metadata["id"]) as the join key across lists.
    """
    scores: dict[int, float] = {}
    docs_by_id: dict[int, Document] = {}

    for result_list in (vector_results, bm25_results):
        for rank, doc in enumerate(result_list, start=1):
            chunk_id = doc.metadata["id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            docs_by_id.setdefault(chunk_id, doc)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

    logger.info(
        "reciprocal_rank_fusion: %d vector result(s), %d bm25 result(s), %d unique chunk(s), returning top %d",
        len(vector_results), len(bm25_results), len(ranked_ids), top_n,
    )

    fused = []
    for chunk_id in ranked_ids[:top_n]:
        doc = docs_by_id[chunk_id]
        doc.metadata["rrf_score"] = scores[chunk_id]
        fused.append(doc)

    return fused


if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

    from app.retrieval.bm25 import bm25_search
    from app.retrieval.vector import similarity_search

    logging.basicConfig(level=logging.INFO)

    query = "business expense meals"
    vec = similarity_search(query)
    kw = bm25_search(query)
    results = reciprocal_rank_fusion(vec, kw)
    for doc in results:
        print(doc.metadata, doc.page_content[:80])
