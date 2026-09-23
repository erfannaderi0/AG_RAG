# app/retrieval/bm25.py
"""
Keyword search over document_chunks using Postgres full-text search:
plainto_tsquery against the chunk_tsv generated column,
ranked with ts_rank_cd. Mirrors vector.py's similarity_search() shape and
return format so fusion.py can treat both result lists uniformly.
"""

import logging
import sys
from pathlib import Path

from langchain_core.documents import Document

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from db.connection import get_connection

logger = logging.getLogger(__name__)


def bm25_search(query: str, k: int = 5) -> list[Document]:
    """
    Run keyword search against chunk_tsv and return the top-k matching
    chunks as Document objects, ranked by ts_rank_cd descending.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dc.id, dc.chunk_text, dc.doc_id, dc.version_number, dc.chunk_index,
                       ts_rank_cd(dc.chunk_tsv, plainto_tsquery('english', %s)) AS rank, d.title
                FROM document_chunks dc
                JOIN documents d ON d.doc_id = dc.doc_id
                WHERE dc.chunk_tsv @@ plainto_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, query, k),
            )
            rows = cur.fetchall()

    logger.info("bm25_search returned %d result(s) for query=%r", len(rows), query)

    return [
        Document(
            page_content=row[1],
            metadata={"id": row[0], "doc_id": row[2], "version_number": row[3], "chunk_index": row[4], "rank": row[5], "title": row[6]},
        )
        for row in rows
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = bm25_search("what is the standard limit of business expense for meals? ")
    for doc in results:
        print(doc.metadata, doc.page_content[:80])
