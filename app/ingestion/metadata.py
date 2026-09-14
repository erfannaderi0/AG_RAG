# app/ingestion/metadata.py
"""
Normalizes raw Drive/Docs metadata (as returned by loaders.py) into a
consistent shape the rest of the pipeline can rely on — doc_id, title,
source URL, and last_modified as a proper datetime object.
"""

import logging
import re
from datetime import datetime
from datetime import datetime, timezone

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Drive URLs look like: https://docs.google.com/document/d/<FILE_ID>/edit
_DRIVE_ID_PATTERN = re.compile(r"/d/([a-zA-Z0-9_-]+)")


def _extract_doc_id(document: Document) -> str:
    """
    GoogleDriveLoader's metadata typically includes an 'id' field
    directly, but fall back to parsing it out of the source URL if
    that key is ever missing or renamed between library versions.
    """
    metadata = document.metadata

    if "id" in metadata and metadata["id"]:
        return metadata["id"]

    source = metadata.get("source", "")
    match = _DRIVE_ID_PATTERN.search(source)
    if match:
        return match.group(1)

    raise ValueError(f"Could not determine doc_id from metadata: {metadata}")


def _parse_last_modified(document: Document) -> datetime:
    """
    GoogleDriveLoader doesn't always populate a modified-time field by
    default. Falls back to the current time when unavailable — this
    means last_modified reflects "when we ingested it," not the real
    Drive edit time, for any doc where the field is missing.
    """
    raw = document.metadata.get("modifiedTime") or document.metadata.get("when")
    if not raw:
        logger.warning(
            "No modifiedTime found for doc_id=%s, falling back to now()",
            document.metadata.get("id", "unknown"),
        )
        return datetime.now(timezone.utc)

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.warning("Could not parse last_modified value: %r", raw)
        return datetime.now(timezone.utc)


def normalize_metadata(document: Document) -> Document:
    """
    Return a new Document with a cleaned, consistent metadata dict.
    Original Drive fields are preserved under 'raw_metadata' in case
    something downstream needs them later.
    """
    doc_id = _extract_doc_id(document)
    title = document.metadata.get("title", "Untitled")
    source = document.metadata.get("source", "")
    last_modified = _parse_last_modified(document)

    clean_metadata = {
        "doc_id": doc_id,
        "title": title,
        "source": source,
        "last_modified": last_modified,
        "raw_metadata": document.metadata,
    }

    return Document(page_content=document.page_content, metadata=clean_metadata)


def normalize_all(documents: list[Document]) -> list[Document]:
    return [normalize_metadata(doc) for doc in documents]
