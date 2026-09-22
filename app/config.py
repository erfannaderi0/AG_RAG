# app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # project root = D:\github_projects\AG_RAG

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # <-- don't crash on unknown .env keys
    )

    # --- things your code actually needs ---
    groq_api_key: str
    google_drive_folder_id: str
    database_url: str
    
    # --- Embeddings (local) ---
    embedding_model_name: str = str(BASE_DIR / "models" / "all-MiniLM-L6-v2")
    reranker_model_name: str = str(BASE_DIR / "models" / "ms-marco-MiniLM-L6-v2")
    embedding_dim: int = 384

    # --- Google OAuth fields from .env ---
    gdoc_client_id: str | None = None
    gdoc_project_id: str | None = None
    gdoc_auth_url: str | None = None
    gdoc_token_url: str | None = None
    gdoc_auth_provider: str | None = None
    gdoc_client_secret: str | None = None
    gdoc_redirect_uris: str | None = None
    google_credentials_path: str
    google_token_path: str
    
    # --- Generation (Groq via langchain_groq) ---
    groq_model_name: str = "openai/gpt-oss-120b"
    groq_temperature: float = 0.1
    groq_max_tokens: int = 1024

settings = Settings()
