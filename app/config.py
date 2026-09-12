# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str

    # LLM (generation)
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Embeddings (local)
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Google Drive / Docs ingestion (OAuth desktop app)
    google_credentials_path: str = "./client_secret.json"
    google_token_path: str = "./token.json"
    google_drive_folder_id: str


settings = Settings()
