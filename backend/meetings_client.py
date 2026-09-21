"""Client d'ingestion des réunions et invitations d'agenda (Gmail et Google Calendar)."""

import datetime
import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

from backend.gmail_client import extract_body_from_payload

logger = logging.getLogger("MeetingsClient")


def fetch_upcoming_meetings(
    creds,
    max_results: int = 15,
) -> List[Dict[str, Any]]:
    """Récupère les invitations de réunion récentes et à venir.

    Interroge Gmail pour capter les e-mails d'invitations (invite.ics, notifications Google Calendar,
    mises à jour d'agenda) et tente également Google Calendar API si les permissions sont présentes.
    """
    if not creds:
        logger.warning("Identifiants absents. Ingestion des réunions annulée.")
        return []

    meetings: List[Dict[str, Any]] = []

    # 1. Tentative d'appel direct Google Calendar API (si le scope calendar.readonly est actif)
    try:
        service_cal = build("calendar", "v3", credentials=creds, cache_discovery=False)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        events_result = (
            service_cal.events()
            .list(
                calendarId="primary",
                timeMin=now_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        logger.info(f"{len(events)} événements récupérés directement via Google Calendar API.")
        for ev in events:
            summary = ev.get("summary", "Réunion sans titre")
            start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
            end = ev.get("end", {}).get("dateTime", ev.get("end", {}).get("date", ""))
            organizer = ev.get("organizer", {}).get("displayName") or ev.get("organizer", {}).get("email", "Inconnu")
            attendees = [a.get("displayName") or a.get("email") for a in ev.get("attendees", []) if a.get("email")]
            desc = ev.get("description", "")
            cal_url = ev.get("htmlLink", "https://calendar.google.com")

            meetings.append(
                {
                    "source": "Google Calendar",
                    "id": ev.get("id", ""),
                    "url": cal_url,
                    "date_heure": f"{start} - {end}",
                    "organisateur": organizer,
                    "participants": attendees,
                    "sujet": summary,
                    "contenu": desc or summary,
                }
            )
    except Exception as cal_err:
        logger.debug(f"Google Calendar API non accessible directement (fallback sur Gmail) : {cal_err}")

    # 2. Récupération des invitations et ordres du jour via Gmail API
    try:
        service_gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
        query = (
            'filename:invite.ics OR subject:Invitation OR "calendar-notification" '
            'OR subject:"Mise à jour :" OR subject:"Point hebdo" OR subject:"Hebdo"'
        )
        res = (
            service_gmail.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = res.get("messages", [])
        logger.info(f"{len(messages)} e-mails d'invitations de réunions trouvés dans Gmail.")

        import time
        for msg_meta in messages:
            msg_id = msg_meta["id"]
            try:
                time.sleep(0.05)
                msg = (
                    service_gmail.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
            except Exception as get_err:
                logger.debug(f"Impossible de récupérer l'invitation {msg_id}: {get_err}")
                continue

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            subject = headers.get("subject", "Réunion")
            sender = headers.get("from", "Inconnu")
            date_str = headers.get("date", "")
            snippet = msg.get("snippet", "")
            body = extract_body_from_payload(msg.get("payload", {})) or snippet
            thread_id = msg.get("threadId", msg_id)
            gmail_url = f"https://mail.google.com/mail/u/0/#all/{thread_id}"

            if len(body) > 3000:
                body = body[:3000] + "\n... [tronqué]"

            meetings.append(
                {
                    "source": "Gmail (Invitation Agenda)",
                    "id": msg_id,
                    "url": gmail_url,
                    "date": date_str,
                    "expediteur": sender,
                    "sujet": subject,
                    "contenu": body,
                }
            )

    except Exception as gmail_err:
        logger.error(f"Erreur lors de la récupération des réunions via Gmail : {gmail_err}")

    return meetings
