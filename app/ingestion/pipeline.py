# app/ingestion/pipeline.py
"""
Orchestrates the full ingestion flow: load -> normalize metadata ->
hash -> check version -> (skip if unchanged) -> redact PII -> chunk ->
embed & store -> purge stale chunks -> record new version.

Run directly for manual testing, or import run_pipeline() from
scripts/ingest.py for the real entry point.
"""

import logging
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from app.ingestion.loaders import load_documents
from app.ingestion.metadata import normalize_all
from app.ingestion.hashing import hash_document
from app.ingestion.versioning import check_version, get_next_version, record_version, VersionStatus
from app.ingestion.pii import redact_pii
from app.ingestion.chunking import chunk_document
from app.retrieval.vector import store_chunks, purge_old_versions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pipeline() -> dict:
    """
    Run one full ingestion pass. Returns a summary dict with counts,
    for visibility into what happened.
    """
    summary = {"new": 0, "changed": 0, "unchanged": 0, "failed": 0}

    raw_documents = load_documents()
    documents = normalize_all(raw_documents)

    for document in documents:
        doc_id = document.metadata["doc_id"]
        title = document.metadata["title"]
        last_modified = document.metadata["last_modified"]

        try:
            content_hash = hash_document(document)
            status = check_version(doc_id, content_hash)

            if status == VersionStatus.UNCHANGED:
                logger.info("Skipping unchanged doc_id=%s", doc_id)
                summary["unchanged"] += 1
                continue

            next_version = get_next_version(doc_id)
            
            # record_version now runs BEFORE chunk storage, so the FK
            # from document_chunks -> documents is satisfied. Trade-off:
            # if store_chunks() fails after this line, `documents` will
            # show the new version even though chunks weren't stored.
            # Acceptable for now; worth hardening later with a shared
            # transaction across record_version + store_chunks.
            record_version(doc_id, title, content_hash, last_modified)

            redacted = redact_pii(document)
            chunks = chunk_document(redacted)

            for chunk in chunks:
                chunk.metadata["version_number"] = next_version

            store_chunks(chunks)
            purge_old_versions(doc_id, next_version)

            if status == VersionStatus.NEW:
                summary["new"] += 1
            else:
                summary["changed"] += 1

            logger.info("Successfully ingested doc_id=%s (version %d)", doc_id, next_version)

        except Exception:
            logger.exception("Failed to ingest doc_id=%s", doc_id)
            summary["failed"] += 1
            continue

    logger.info("Pipeline run complete: %s", summary)
    return summary


if __name__ == "__main__":
    run_pipeline()
