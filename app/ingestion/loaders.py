# app/ingestion/loaders.py
"""
Loads Google Docs from a specified Drive folder using LangChain's
GoogleDriveLoader. Returns raw LangChain Document objects — no chunking,
hashing, or metadata enrichment happens here; that's handled by later
stages in the ingestion pipeline.
"""

import logging
from typing import List
import sys
from pathlib import Path
import os

from langchain_core.documents import Document
from langchain_google_community import GoogleDriveLoader

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from app.config import settings

logger = logging.getLogger(__name__)


def load_documents() -> List[Document]:
    """
    Load all Google Docs from the configured Drive folder.

    Returns:
        List of Document objects, each with:
            - page_content: extracted text of the doc
            - metadata: Drive-provided fields (id, title, source, etc.)

    Raises:
        Propagates any auth/API errors from GoogleDriveLoader so the
        pipeline caller can decide how to handle a failed ingestion run.
    """
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS", str(settings.google_credentials_path)
    )

    loader = GoogleDriveLoader(
        folder_id=settings.google_drive_folder_id,
        credentials_path=settings.google_credentials_path,
        token_path=settings.google_token_path,
        file_types=["document"],
        recursive=False,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )

    logger.info(
        "Loading documents from Drive folder: %s",
        settings.google_drive_folder_id,
    )

    documents = loader.load()

    logger.info("Loaded %d document(s)", len(documents))

    return documents
