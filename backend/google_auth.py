"""Gestion de l'authentification Google Workspace (OAuth2 & Service Account)."""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from backend.config import (
    BASE_DIR,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_CREDENTIALS_BASE64,
    GOOGLE_DELEGATED_USER_EMAIL,
    GOOGLE_REFRESH_TOKEN,
    GOOGLE_SCOPES,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SERVICE_ACCOUNT_KEY,
)

logger = logging.getLogger("GoogleAuth")


def get_google_credentials() -> Optional[Credentials]:
    """Résout et instancie les identifiants d'accès Google de manière flexible.

    Priorités d'authentification :
    1. Chaîne Base64 (GOOGLE_CREDENTIALS_BASE64) - idéal pour GitHub Secrets.
    2. JSON Service Account explicite (GOOGLE_SERVICE_ACCOUNT_KEY).
    3. Fichier Service Account local (GOOGLE_SERVICE_ACCOUNT_FILE).
    4. Variables OAuth2 (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN).
    5. Fichier local 'token.json' (généré par setup_google_auth.py).
    """
    creds = None

    # 1. Base64 Credentials (GitHub Actions / Cloud)
    if GOOGLE_CREDENTIALS_BASE64:
        try:
            logger.info("Décodage des identifiants depuis GOOGLE_CREDENTIALS_BASE64...")
            decoded_bytes = base64.b64decode(GOOGLE_CREDENTIALS_BASE64)
            data = json.loads(decoded_bytes.decode("utf-8"))

            if data.get("type") == "service_account":
                creds = service_account.Credentials.from_service_account_info(
                    data, scopes=GOOGLE_SCOPES
                )
                if GOOGLE_DELEGATED_USER_EMAIL:
                    creds = creds.with_subject(GOOGLE_DELEGATED_USER_EMAIL)
                return creds
            elif "refresh_token" in data or "token" in data:
                creds = Credentials.from_authorized_user_info(data, scopes=GOOGLE_SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                return creds
        except Exception as e:
            logger.error(f"Échec de chargement de GOOGLE_CREDENTIALS_BASE64: {e}")

    # 2. Service Account JSON brut dans l'environnement
    if GOOGLE_SERVICE_ACCOUNT_KEY:
        try:
            logger.info("Chargement des identifiants depuis GOOGLE_SERVICE_ACCOUNT_KEY...")
            data = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)
            creds = service_account.Credentials.from_service_account_info(
                data, scopes=GOOGLE_SCOPES
            )
            if GOOGLE_DELEGATED_USER_EMAIL:
                creds = creds.with_subject(GOOGLE_DELEGATED_USER_EMAIL)
            return creds
        except Exception as e:
            logger.error(f"Erreur chargement GOOGLE_SERVICE_ACCOUNT_KEY: {e}")

    # 3. Fichier Service Account local
    sa_path = Path(GOOGLE_SERVICE_ACCOUNT_FILE)
    if not sa_path.is_absolute():
        sa_path = BASE_DIR / sa_path

    if sa_path.exists():
        try:
            logger.info(f"Chargement du compte de service depuis : {sa_path}")
            creds = service_account.Credentials.from_service_account_file(
                str(sa_path), scopes=GOOGLE_SCOPES
            )
            if GOOGLE_DELEGATED_USER_EMAIL:
                creds = creds.with_subject(GOOGLE_DELEGATED_USER_EMAIL)
            return creds
        except Exception as e:
            logger.error(f"Erreur lecture fichier service account {sa_path}: {e}")

    # 4. Variables d'environnement OAuth2 directes
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN:
        try:
            logger.info("Chargement via variables OAuth2 (Client ID / Refresh Token)...")
            creds = Credentials(
                token=None,
                refresh_token=GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=GOOGLE_SCOPES,
            )
            if creds.expired or not creds.valid:
                creds.refresh(Request())
            return creds
        except Exception as e:
            logger.error(f"Erreur rafraîchissement OAuth2 d'environnement: {e}")

    # 5. Fichier local token.json
    token_path = BASE_DIR / "token.json"
    if token_path.exists():
        try:
            logger.info(f"Chargement du jeton OAuth depuis {token_path}...")
            creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
        except Exception as e:
            logger.error(f"Erreur chargement token.json: {e}")

    logger.warning(
        "Aucun identifiant Google Workspace valide n'a pu être résolu. "
        "Utilisez setup_google_auth.py pour configurer l'accès ou activez le mode --mock."
    )
    return None
