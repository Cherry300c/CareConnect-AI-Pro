import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "CareConnect AI Pro"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "careconnect_ai_pro.db"

DEFAULT_ADMIN_EMAIL = os.getenv(
    "DEFAULT_ADMIN_EMAIL",
    "admin@careconnect.local"
)
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")

APP_ROLES = ["Patient", "Doctor", "Admin"]

# Gemini API Key
# Store the real key in .env or your deployment platform's secrets.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_TEXT_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

GEMINI_VISION_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

APP_DISCLAIMER = (
    "CareConnect AI Pro supports healthcare navigation and triage. "
    "It is not a final medical diagnosis."
)