"""Client d'ingestion Gmail pour extraire les e-mails techniques des dernières 24h."""

import base64
import datetime
import logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from googleapiclient.discovery import build

from backend.config import GMAIL_LABELS_FILTER

logger = logging.getLogger("GmailClient")


def clean_html_content(html_text: str) -> str:
    """Nettoie le HTML pour extraire un texte clair et réduire l'usage de tokens."""
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "meta", "noscript", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception:
        return html_text


def extract_body_from_payload(payload: Dict[str, Any]) -> str:
    """Extrait récursivement le corps de l'e-mail (plain text ou html nettoyé)."""
    body_text = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            part_body = part.get("body", {})
            data = part_body.get("data")

            if mime_type == "text/plain" and data:
                try:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    pass
            elif mime_type == "text/html" and data:
                try:
                    html_raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    body_text = clean_html_content(html_raw)
                except Exception:
                    pass
            elif "parts" in part:
                nested = extract_body_from_payload(part)
                if nested:
                    return nested

    data = payload.get("body", {}).get("data")
    if data:
        try:
            raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if "<html>" in raw.lower() or "<div>" in raw.lower():
                return clean_html_content(raw)
            return raw
        except Exception:
            pass

    return body_text


def fetch_recent_emails(
    creds,
    hours: int = 24,
    labels: Optional[List[str]] = None,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """Récupère les e-mails des dernières 24h ciblant les libellés de supervision.

    Labels cibles typiques : 'OneStock via RUN', 'Notification_DSI', 'OPCON', 'trt_stambia'.
    """
    if not creds:
        logger.warning("Identifiants Google absents. Ingestion Gmail annulée.")
        return []

    target_labels = labels or GMAIL_LABELS_FILTER
    logger.info(f"Recherche Gmail sur les dernières {hours}h avec filtres : {target_labels}")

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        # Construction de la requête temporelle et thématique
        # newer_than:1d ou recherche par labels
        query_parts = []
        label_queries = []
        for lbl in target_labels:
            clean_lbl = lbl.replace('"', "").strip()
            label_queries.append(f'label:"{clean_lbl}"')
            label_queries.append(f'"{clean_lbl}"')

        combined_label_query = " OR ".join(label_queries)
        query = f"newer_than:{max(1, hours // 24)}d AND ({combined_label_query})"

        logger.info(f"Requête Gmail exécutée : {query}")

        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            # Fallback plus large si les labels personnalisés ne sont pas configurés à l'identique
            fallback_query = f"newer_than:{max(1, hours // 24)}d (OneStock OR DSI OR OPCON OR Stambia OR Alerte OR Incident)"
            logger.info(f"Aucun message avec labels stricts. Tentative avec fallback : {fallback_query}")
            fallback_resp = (
                service.users()
                .messages()
                .list(userId="me", q=fallback_query, maxResults=max_results)
                .execute()
            )
            messages = fallback_resp.get("messages", [])

        logger.info(f"{len(messages)} messages trouvés sur la période.")

        results = []
        for msg_meta in messages:
            msg_id = msg_meta["id"]
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            subject = headers.get("subject", "(Sans objet)")
            sender = headers.get("from", "Inconnu")
            date_str = headers.get("date", "")
            snippet = msg.get("snippet", "")
            body = extract_body_from_payload(msg.get("payload", {})) or snippet

            # Tronquer le corps si excessif (éviter dépassement de contexte inutile)
            if len(body) > 3000:
                body = body[:3000] + "\n... [contenu tronqué]"

            results.append(
                {
                    "source": "Gmail",
                    "id": msg_id,
                    "date": date_str,
                    "expediteur": sender,
                    "sujet": subject,
                    "extrait": snippet,
                    "contenu": body,
                }
            )

        return results

    except Exception as e:
        logger.error(f"Erreur lors de la récupération Gmail : {e}")
        return []
