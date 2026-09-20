"""Client d'ingestion Google Chat pour extraire les échanges techniques récents."""

import datetime
import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

from backend.config import GOOGLE_CHAT_SPACES

logger = logging.getLogger("ChatClient")


def fetch_recent_chat_messages(
    creds,
    hours: int = 24,
    space_names: Optional[List[str]] = None,
    max_messages_per_space: int = 30,
) -> List[Dict[str, Any]]:
    """Récupère les messages échangés dans Google Chat sur les dernières 24h.

    Supporte les espaces explicitement renseignés ou liste les espaces accessibles.
    """
    if not creds:
        logger.warning("Identifiants Google absents. Ingestion Google Chat annulée.")
        return []

    logger.info(f"Recherche Google Chat sur les dernières {hours}h...")
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)

    try:
        service = build("chat", "v1", credentials=creds, cache_discovery=False)

        # 1. Résolution des espaces ciblés
        target_spaces = space_names or GOOGLE_CHAT_SPACES
        spaces_to_scan = []

        if target_spaces:
            for s in target_spaces:
                s_clean = s.strip()
                if not s_clean.startswith("spaces/"):
                    s_clean = f"spaces/{s_clean}"
                spaces_to_scan.append({"name": s_clean, "displayName": s_clean})
        else:
            try:
                spaces_res = service.spaces().list(pageSize=20).execute()
                spaces_to_scan = spaces_res.get("spaces", [])
                logger.info(f"{len(spaces_to_scan)} espaces Google Chat détectés.")
            except Exception as space_err:
                logger.warning(
                    f"Impossible de lister automatiquement les espaces Chat: {space_err}. "
                    "Configurez GOOGLE_CHAT_SPACES si vous utilisez un compte avec restrictions."
                )
                return []

        all_messages = []

        for space in spaces_to_scan:
            space_id = space.get("name")
            display_name = space.get("displayName", space_id)

            try:
                msg_res = (
                    service.spaces()
                    .messages()
                    .list(parent=space_id, pageSize=max_messages_per_space)
                    .execute()
                )

                messages = msg_res.get("messages", [])
                for msg in messages:
                    create_time_str = msg.get("createTime", "")
                    # Filtre temporel (ex: 2026-09-20T10:15:30.000Z)
                    if create_time_str:
                        try:
                            # Parsing ISO format
                            ts = datetime.datetime.fromisoformat(
                                create_time_str.replace("Z", "+00:00")
                            )
                            if ts < cutoff_time:
                                continue
                        except Exception:
                            pass

                    text = msg.get("text", "").strip()
                    sender = msg.get("sender", {}).get("displayName", "Membre Équipe")

                    if text:
                        clean_space = (space_id or "").replace("spaces/", "")
                        room_url = f"https://chat.google.com/room/{clean_space}" if clean_space else "https://chat.google.com"
                        all_messages.append(
                            {
                                "source": "Google Chat",
                                "espace": display_name,
                                "url": room_url,
                                "date": create_time_str,
                                "expediteur": sender,
                                "message": text,
                            }
                        )

            except Exception as err:
                logger.debug(f"Accès restreint ou vide pour l'espace {display_name}: {err}")

        logger.info(f"{len(all_messages)} messages Google Chat collectés.")
        return all_messages

    except Exception as e:
        logger.error(f"Erreur globale d'accès à Google Chat API : {e}")
        return []
