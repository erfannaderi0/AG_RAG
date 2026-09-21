# app/retrieval/pipeline.py
"""
Orchestrates the full retrieval flow: vector search + BM25 search ->
reciprocal rank fusion -> cross-encoder reranking.

Run directly for manual testing, or import retrieve() as the entry point
for graph/nodes.py's retrieval node.
"""

import logging
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from langchain_core.documents import Document

from app.retrieval.bm25 import bm25_search
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranking import rerank
from app.retrieval.vector import similarity_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    vector_k: int = 5,
    bm25_k: int = 5,
    rrf_k: int = 60,
    rrf_top_n: int = 10,
    rerank_top_n: int = 5,
) -> list[Document]:
    """
    Run one full retrieval pass for a query: vector search + BM25 search,
    fused with RRF, then reranked with a cross-encoder. Returns the final
    top-ranked Documents, ready for the generation step.
    """
    vector_results = similarity_search(query, k=vector_k)
    bm25_results = bm25_search(query, k=bm25_k)

    fused = reciprocal_rank_fusion(vector_results, bm25_results, k=rrf_k, top_n=rrf_top_n)

    reranked = rerank(query, fused, top_n=rerank_top_n)

    logger.info(
        "retrieve: query=%r -> %d vector, %d bm25, %d fused, %d final",
        query, len(vector_results), len(bm25_results), len(fused), len(reranked),
    )

    return reranked


if __name__ == "__main__":
    results = retrieve("business expense meals")
    for doc in results:
        print(doc.metadata, doc.page_content[:80])
