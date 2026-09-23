# app/retrieval/vector.py
"""
Owns the document_chunks table: embedding chunk text via the local
all-MiniLM-L6-v2 model, storing (chunk_text, embedding, doc_id,
version_number), purging stale versions on re-ingestion, and running
similarity search at query time.
"""

import logging

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from pgvector.psycopg import register_vector
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from app.config import settings
from db.connection import get_connection

logger = logging.getLogger(__name__)

_embeddings = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Lazily instantiate the embedding model once, reused across calls."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model_name)
    return _embeddings


def store_chunks(chunks: list[Document]) -> int:
    """
    Embed and insert a list of chunk Documents into document_chunks.
    Each chunk's metadata is expected to already contain doc_id and a
    version_number (set by pipeline.py before calling this).

    Returns the number of chunks inserted.
    """
    if not chunks:
        return 0

    embeddings_model = _get_embeddings()
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings_model.embed_documents(texts)

    with get_connection() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for chunk, vector in zip(chunks, vectors):
                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (doc_id, version_number, chunk_index, chunk_text, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        chunk.metadata["doc_id"],
                        chunk.metadata["version_number"],
                        chunk.metadata["chunk_index"],
                        chunk.page_content,
                        vector,
                    ),
                )
        conn.commit()

    logger.info("Stored %d chunk(s)", len(chunks))
    return len(chunks)


def purge_old_versions(doc_id: str, current_version: int) -> int:
    """
    Delete chunks belonging to any version of doc_id older than
    current_version. Called after a successful re-ingestion so stale
    chunks don't linger and pollute retrieval.

    Returns the number of chunks deleted.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM document_chunks
                WHERE doc_id = %s AND version_number < %s
                """,
                (doc_id, current_version),
            )
            deleted = cur.rowcount
        conn.commit()

    if deleted:
        logger.info("Purged %d stale chunk(s) for doc_id=%s", deleted, doc_id)
    return deleted


def similarity_search(query: str, k: int = 5) -> list[Document]:
    """
    Embed the query and return the top-k most similar chunks as
    Document objects, using pgvector's cosine distance operator.
    """
    embeddings_model = _get_embeddings()
    query_vector = embeddings_model.embed_query(query)

    with get_connection() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dc.id, dc.chunk_text, dc.doc_id, dc.version_number, dc.chunk_index,
                    dc.embedding <=> %s::vector AS distance, d.title
                FROM document_chunks dc
                JOIN documents d ON d.doc_id = dc.doc_id
                ORDER BY distance
                LIMIT %s
                """,
                (query_vector, k),
            )
            rows = cur.fetchall()

    return [
        Document(
            page_content=row[1],
            metadata={"id": row[0], "doc_id": row[2], "version_number": row[3], "chunk_index": row[4], "distance": row[5], "title": row[6]},
        )
        for row in rows
    ]
