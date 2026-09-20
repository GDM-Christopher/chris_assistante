"""Configuration centralisée pour l'application de supervision technique."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Chargement du fichier .env s'il existe (recherche à la racine du projet ou répertoire parent)
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# --- Clés API & Fournisseurs Cloud ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# --- Google Workspace Auth ---
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json").strip()
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "").strip()
GOOGLE_CREDENTIALS_BASE64 = os.getenv("GOOGLE_CREDENTIALS_BASE64", "").strip()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
GOOGLE_DELEGATED_USER_EMAIL = os.getenv("GOOGLE_DELEGATED_USER_EMAIL", "").strip()

# Scopes d'autorisation Google Workspace requis
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
]

# --- Paramètres Ingestion ---
GMAIL_INGEST_ALL = os.getenv("GMAIL_INGEST_ALL", "true").lower() in ("true", "1", "yes")
GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", "100"))

GMAIL_LABELS_FILTER = [
    label.strip()
    for label in os.getenv(
        "GMAIL_LABELS_FILTER",
        "OneStock, Notification_DSI, OPCON, Stambia, Supply, Snowflake, Implantation, WinWig",
    ).split(",")
    if label.strip()
]

GMAIL_LOOKBACK_HOURS = int(os.getenv("GMAIL_LOOKBACK_HOURS", "48"))
GOOGLE_CHAT_SPACES = [
    space.strip()
    for space in os.getenv("GOOGLE_CHAT_SPACES", "").split(",")
    if space.strip()
]
