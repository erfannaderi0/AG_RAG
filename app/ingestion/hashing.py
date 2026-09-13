# app/ingestion/hashing.py
"""
Computes a stable content hash for each document, used by versioning.py
to detect whether a document has actually changed since the last
ingestion run (vs. just being re-fetched with no real edits).
"""

import hashlib

from langchain_core.documents import Document


def _normalize_text(text: str) -> str:
    """
    Normalize text before hashing so that inconsequential formatting
    differences (trailing whitespace, line-ending style, repeated blank
    lines) don't produce a different hash for content that hasn't
    meaningfully changed.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    normalized = "\n".join(lines).strip()
    return normalized


def compute_content_hash(text: str) -> str:
    """
    Return a SHA-256 hex digest of normalized document text.
    """
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_document(document: Document) -> str:
    """
    Convenience wrapper: compute the content hash directly from a
    LangChain Document's page_content.
    """
    return compute_content_hash(document.page_content)
