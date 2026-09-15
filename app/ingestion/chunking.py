# app/ingestion/chunking.py
"""
Splits document text into retrieval-sized chunks using LangChain's
RecursiveCharacterTextSplitter. Runs after PII redaction — chunks
inherit and extend the parent document's metadata (doc_id, title, etc.)
plus a chunk_index so retrieval/vector.py can store them
identifiably.
"""

import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Chunk size in characters (not tokens) — RecursiveCharacterTextSplitter
# operates on character count by default. 1000/150 is a common starting
# point for general prose; not tuned to your actual docs yet.
_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 150

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=_CHUNK_SIZE,
    chunk_overlap=_CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_document(document: Document) -> list[Document]:
    """
    Split a single Document into smaller Document chunks. Each chunk
    keeps the parent's full metadata plus a chunk_index marking its
    position within the parent doc.
    """
    chunks = _splitter.split_text(document.page_content)

    chunk_documents = []
    for i, chunk_text in enumerate(chunks):
        chunk_metadata = {**document.metadata, "chunk_index": i}
        chunk_documents.append(
            Document(page_content=chunk_text, metadata=chunk_metadata)
        )

    logger.info(
        "Split doc_id=%s into %d chunk(s)",
        document.metadata.get("doc_id", "unknown"),
        len(chunk_documents),
    )

    return chunk_documents


def chunk_all(documents: list[Document]) -> list[Document]:
    """
    Chunk a list of documents, returning a flat list of all chunks
    across all documents (not grouped by parent).
    """
    all_chunks = []
    for document in documents:
        all_chunks.extend(chunk_document(document))
    return all_chunks
