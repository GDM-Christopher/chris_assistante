"""Client d'ingestion Google Chat pour extraire les échanges techniques récents."""

import datetime
import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

from backend.config import GOOGLE_CHAT_SPACES

logger = logging.getLogger("ChatClient")

# Correspondance des noms conviviaux pour les espaces techniques et conversations de groupe
KNOWN_SPACES_MAP = {
    "spaces/AAAAxgmHsuA": "La DOSI - Equipe Data / IA",
    "spaces/AAAAerZzJKI": "Roxane, Salim, Céline, Ella, ... (Groupe)",
    "spaces/AAQA5BpGcuU": "Roxane, Salim, Marine, Laura, ... (Groupe)",
    "spaces/AAQAJNw_z10": "Roxane, Salim, Elisabeth (Groupe)",
    "spaces/AAAAC5-u9Fw": "La DOSI - Espace PRO",
    "spaces/AAAAQIFr7uA": "Exploitation - RUN",
    "spaces/AAQAnKMzDkQ": "S/4 Incidents PROD - Transition DEV => RUN",
    "spaces/AAAAgmlx2rE": "INTERNES - IT",
    "spaces/AAAAIeO0dyM": "La DOSI - Espace PERSO",
}


def fetch_recent_chat_messages(
    creds,
    hours: int = 24,
    space_names: Optional[List[str]] = None,
    max_messages_per_space: int = 30,
) -> List[Dict[str, Any]]:
    """Récupère les messages échangés dans Google Chat sur la fenêtre temporelle.

    Utilise orderBy='createTime desc' pour que les messages les plus récents
    (des dernières minutes / heures) soient immédiatement ingérés et traités.
    """
    if not creds:
        logger.warning("Identifiants Google absents. Ingestion Google Chat annulée.")
        return []

    # Ajustement automatique du lookback le lundi pour couvrir le week-end et vendredi
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() == 0 and hours < 72:
        effective_hours = 96
        logger.info(
            f"Lundi détecté : extension automatique du lookback Chat de {hours}h à {effective_hours}h "
            "pour couvrir le week-end et vendredi."
        )
    else:
        effective_hours = hours

    cutoff_time = now - datetime.timedelta(hours=effective_hours)
    logger.info(f"Recherche Google Chat sur les dernières {effective_hours}h (depuis {cutoff_time.strftime('%Y-%m-%d %H:%M:%S UTC')})...")

    try:
        service = build("chat", "v1", credentials=creds, cache_discovery=False)

        # 1. Résolution des espaces ciblés
        target_spaces_input = space_names or GOOGLE_CHAT_SPACES
        spaces_to_scan = []

        if target_spaces_input:
            for s in target_spaces_input:
                s_clean = s.strip()
                if not s_clean:
                    continue
                if not s_clean.startswith("spaces/"):
                    s_clean = f"spaces/{s_clean}"

                friendly_name = KNOWN_SPACES_MAP.get(s_clean, s_clean)
                spaces_to_scan.append({"name": s_clean, "displayName": friendly_name})
        else:
            try:
                spaces_res = service.spaces().list(pageSize=50).execute()
                spaces_to_scan = spaces_res.get("spaces", [])
                logger.info(f"{len(spaces_to_scan)} espaces Google Chat détectés.")
            except Exception as space_err:
                logger.warning(
                    f"Impossible de lister automatiquement les espaces Chat: {space_err}. "
                    "Utilisation des espaces par défaut."
                )
                spaces_to_scan = [
                    {"name": k, "displayName": v} for k, v in KNOWN_SPACES_MAP.items()
                ]

        all_messages = []

        for space in spaces_to_scan:
            space_id = space.get("name")
            display_name = space.get("displayName") or KNOWN_SPACES_MAP.get(space_id) or space_id

            try:
                # IMPORTANT : orderBy="createTime desc" garantit l'obtention des messages récents en premier
                msg_res = (
                    service.spaces()
                    .messages()
                    .list(
                        parent=space_id,
                        pageSize=max_messages_per_space,
                        orderBy="createTime desc",
                    )
                    .execute()
                )

                messages = msg_res.get("messages", [])
                recent_senders = []
                space_messages = []

                for msg in messages:
                    create_time_str = msg.get("createTime", "")
                    if create_time_str:
                        try:
                            ts = datetime.datetime.fromisoformat(
                                create_time_str.replace("Z", "+00:00")
                            )
                            if ts < cutoff_time:
                                # Les messages suivants étant encore plus anciens, on stoppe la boucle pour cet espace
                                break
                        except Exception:
                            pass

                    text = msg.get("text", "").strip()
                    sender = msg.get("sender", {}).get("displayName", "Membre Équipe")
                    if sender and sender not in recent_senders:
                        recent_senders.append(sender)

                    if text:
                        clean_space = (space_id or "").replace("spaces/", "")
                        room_url = (
                            f"https://chat.google.com/room/{clean_space}"
                            if clean_space
                            else "https://chat.google.com"
                        )
                        space_messages.append(
                            {
                                "source": "Google Chat",
                                "espace": display_name,
                                "url": room_url,
                                "date": create_time_str,
                                "expediteur": sender,
                                "message": text,
                            }
                        )

                # Si le nom affiché est un ID brut et qu'on a détecté des expéditeurs récents, enrichir le libellé
                if (not display_name or display_name.startswith("spaces/")) and recent_senders:
                    friendly_name = f"Groupe ({', '.join(recent_senders[:3])})"
                    for m in space_messages:
                        m["espace"] = friendly_name

                all_messages.extend(space_messages)

            except Exception as err:
                logger.debug(f"Accès restreint ou vide pour l'espace {display_name}: {err}")

        logger.info(f"{len(all_messages)} messages Google Chat collectés au total.")
        return all_messages

    except Exception as e:
        logger.error(f"Erreur globale d'accès à Google Chat API : {e}")
        return []
