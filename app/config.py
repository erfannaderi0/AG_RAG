# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # <-- don't crash on unknown .env keys
    )

    # --- things your code actually needs ---
    groq_api_key: str
    google_drive_folder_id: str

    # --- Google OAuth fields from .env ---
    gdoc_client_id: str | None = None
    gdoc_project_id: str | None = None
    gdoc_auth_url: str | None = None
    gdoc_token_url: str | None = None
    gdoc_auth_provider: str | None = None
    gdoc_client_secret: str | None = None
    gdoc_redirect_uris: str | None = None

settings = Settings()
