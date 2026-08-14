"""
app/core/config.py
------------------
Application settings loaded from environment variables / .env file.
"""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Complaint Management System"

    # ------------------------------------------------------------------ #
    # CORS                                                                 #
    # ------------------------------------------------------------------ #
    # Vite dev server runs on 5173 by default.
    # In production, replace with the real frontend origin.
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "sqlite+aiosqlite:///./complaint_db.sqlite"   # Default local SQLite, or postgresql+asyncpg://user:pass@host/db

    # ------------------------------------------------------------------ #
    # Groq LLM                                                             #
    # ------------------------------------------------------------------ #
    GROQ_API_KEY: str = ""
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"
    GROQ_MODEL_LARGE: str = "llama-3.3-70b-versatile"

    # ------------------------------------------------------------------ #
    # File uploads                                                         #
    # ------------------------------------------------------------------ #
    # Local filesystem path for uploaded complaint documents.
    # In production, point this to a mounted volume or set it to a cloud
    # storage bucket prefix (and update core/storage.py accordingly).
    # Path is resolved to absolute at runtime in core/storage.py.
    UPLOAD_DIR: str = "uploads"

    # ------------------------------------------------------------------ #
    # App behaviour                                                        #
    # ------------------------------------------------------------------ #
    DEBUG: bool = False   # Controls SQLAlchemy echo and log verbosity

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
