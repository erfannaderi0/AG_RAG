CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    current_hash TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1,
    last_modified TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_versions (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    version_number INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    version_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
