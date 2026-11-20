
import os
from pathlib import Path
from dotenv import load_dotenv

# Locate project root (web-agent/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()


if not settings.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")
