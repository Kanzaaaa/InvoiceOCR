import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    APP_USERNAME = os.getenv("APP_USERNAME", "admin")
    APP_PASSWORD = os.getenv("APP_PASSWORD", "invoiceocr2026")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        if origin.strip()
    ]
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
    OPENAI_FILE_DETAIL = os.getenv("OPENAI_FILE_DETAIL", "high")

    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "invoices_ocr")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_POOL_MIN_SIZE = int(os.getenv("POSTGRES_POOL_MIN_SIZE", "0"))
    POSTGRES_POOL_MAX_SIZE = int(os.getenv("POSTGRES_POOL_MAX_SIZE", "5"))
    CLIENT_MATCH_THRESHOLD = int(os.getenv("CLIENT_MATCH_THRESHOLD", "92"))

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
    BULK_UPLOAD_MAX_FILES = int(os.getenv("BULK_UPLOAD_MAX_FILES", "20"))

    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads/original")
    EXPORT_FOLDER = BASE_DIR / os.getenv("EXPORT_FOLDER", "exports")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024

    ALLOWED_EXTENSIONS = {"pdf"}
    VALID_INVOICE_TYPES = {
        "invoice",
        "receipt",
        "contract",
        "commission_settlement",
        "credit_note",
        "unknown",
    }

    @classmethod
    def database_url(cls) -> str:
        return (
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )

    @classmethod
    def ensure_directories(cls) -> None:
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
