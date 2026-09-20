"""Gestion de la persistance des rapports quotidiens dans Supabase."""

import logging
from typing import Any, Dict, List, Optional
from supabase import Client, create_client

from backend.config import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger("SupabaseClient")


def get_supabase_client() -> Optional[Client]:
    """Initialise et retourne l'instance du client Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("SUPABASE_URL ou SUPABASE_KEY non configurés.")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Erreur d'initialisation du client Supabase : {e}")
        return None


def upsert_daily_report(report_date: str, raw_summary: Dict[str, Any]) -> bool:
    """Insère ou met à jour le rapport quotidien dans la table 'daily_reports'."""
    client = get_supabase_client()
    if not client:
        raise ConnectionError("Impossible de se connecter à Supabase.")

    payload = {
        "report_date": report_date,
        "raw_summary": raw_summary,
    }

    try:
        logger.info(f"Upsert du rapport pour la date {report_date} dans Supabase...")
        res = client.table("daily_reports").upsert(payload, on_conflict="report_date").execute()
        logger.info(f"Rapport sauvegardé avec succès dans Supabase (ID: {res.data[0].get('id') if res.data else 'OK'}).")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'upsert Supabase : {e}")
        raise e


def get_available_dates() -> List[str]:
    """Récupère la liste de toutes les dates de rapports disponibles, triées par date décroissante."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        res = (
            client.table("daily_reports")
            .select("report_date")
            .order("report_date", desc=True)
            .execute()
        )
        dates = [row["report_date"] for row in (res.data or []) if "report_date" in row]
        return dates
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des dates disponibles : {e}")
        return []


def get_report_by_date(report_date: str) -> Optional[Dict[str, Any]]:
    """Récupère le rapport correspondant à une date spécifique."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = (
            client.table("daily_reports")
            .select("*")
            .eq("report_date", report_date)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du rapport {report_date} : {e}")
        return None


def get_latest_report() -> Optional[Dict[str, Any]]:
    """Récupère le rapport le plus récent présent dans la base."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = (
            client.table("daily_reports")
            .select("*")
            .order("report_date", desc=True)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du dernier rapport : {e}")
        return None
