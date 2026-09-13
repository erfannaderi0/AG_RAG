-- documents: current state, one row per Drive doc
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,        -- Google Drive document ID
    title TEXT NOT NULL,
    current_hash TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    last_modified TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- document_versions: append-only history
CREATE TABLE document_versions (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    version_number INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
