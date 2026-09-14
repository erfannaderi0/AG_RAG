# app/ingestion/pii.py
"""
Detects and redacts PII in document text before it reaches chunking/
embedding/storage. Uses Microsoft Presidio (prebuilt, industry-standard
PII detection) rather than hand-rolled regex — more entity types, better
accuracy, actively maintained.
"""

import logging

from langchain_core.documents import Document
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

logger = logging.getLogger(__name__)

# Entity types to detect and redact. Presidio supports many more
# (CRYPTO, IBAN_CODE, MEDICAL_LICENSE, etc.) — this is a starting set,
# not exhaustive. See note below on why these specifically.
_ENTITIES_TO_REDACT = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "LOCATION",
]

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()


def redact_pii(document: Document) -> Document:
    """
    Scan document text for PII and replace matches with entity-type
    placeholders (e.g. "<PERSON>", "<EMAIL_ADDRESS>"). Returns a new
    Document; original is left untouched. Adds a 'pii_redacted' flag
    to metadata so downstream stages/audits can see redaction occurred.
    """
    results = _analyzer.analyze(
        text=document.page_content,
        entities=_ENTITIES_TO_REDACT,
        language="en",
    )

    if not results:
        return document

    anonymized = _anonymizer.anonymize(
        text=document.page_content,
        analyzer_results=results,
    )

    logger.info(
        "Redacted %d PII entit(y/ies) in doc_id=%s",
        len(results),
        document.metadata.get("doc_id", "unknown"),
    )

    new_metadata = {**document.metadata, "pii_redacted": True}
    return Document(page_content=anonymized.text, metadata=new_metadata)


def redact_all(documents: list[Document]) -> list[Document]:
    return [redact_pii(doc) for doc in documents]
