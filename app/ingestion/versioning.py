# app/ingestion/versioning.py
"""
Compares a freshly computed document hash against the last known hash
in Postgres to decide whether a document is new, changed, or unchanged.
Owns all reads/writes to the documents and document_versions tables.
"""

import logging
from datetime import datetime, timezone
from enum import Enum

import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from app.config import settings

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


from db.connection import get_connection


def check_version(doc_id: str, new_hash: str) -> VersionStatus:
    """
    Look up the current stored hash for doc_id and compare against
    new_hash. Does not write anything — read-only check.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_hash FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            row = cur.fetchone()

    if row is None:
        return VersionStatus.NEW

    stored_hash = row[0]
    if stored_hash == new_hash:
        return VersionStatus.UNCHANGED

    return VersionStatus.CHANGED


def get_next_version(doc_id: str) -> int:
    """
    Read-only: returns what the next version number would be for
    doc_id, without writing anything. Used by pipeline.py to tag
    chunks with the correct version_number before storage.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_version FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            row = cur.fetchone()

    return 1 if row is None else row[0] + 1


def record_version(
    doc_id: str,
    title: str,
    new_hash: str,
    last_modified: datetime,
) -> int:
    """
    Persist a new version: upserts documents (current state) and
    appends a row to document_versions (history). Returns the new
    version number.

    Caller is expected to have already called check_version() and
    confirmed this is a NEW or CHANGED document — calling this for an
    UNCHANGED document will still bump the version, so don't call it
    unconditionally.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_version FROM documents WHERE doc_id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            next_version = 1 if row is None else row[0] + 1

            cur.execute(
                """
                INSERT INTO documents (doc_id, title, current_hash, current_version, last_modified, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    current_hash = EXCLUDED.current_hash,
                    current_version = EXCLUDED.current_version,
                    last_modified = EXCLUDED.last_modified,
                    updated_at = EXCLUDED.updated_at
                """,
                (doc_id, title, new_hash, next_version, last_modified, datetime.now(timezone.utc)),
            )

            cur.execute(
                """
                INSERT INTO document_versions (doc_id, version_number, content_hash, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (doc_id, next_version, new_hash, datetime.now(timezone.utc)),
            )

        conn.commit()

    logger.info("Recorded version %d for doc_id=%s", next_version, doc_id)
    return next_version
