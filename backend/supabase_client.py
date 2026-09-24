"""Gestion de la persistance des rapports quotidiens dans Supabase."""

import json
import logging
import os
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
        
        # Purge automatique des rapports de plus de 30 jours pour ne pas saturer la base
        purge_old_reports(days_retention=30)
        
        return True
    except Exception as e:
        logger.warning(
            f"Table 'daily_reports' non trouvée ou erreur Supabase : {e}. "
            "Les données réelles restent pleinement accessibles via le cache local latest_report.json."
        )
        return False


def purge_old_reports(days_retention: int = 30) -> int:
    """Supprime automatiquement les rapports antérieurs à 'days_retention' jours."""
    client = get_supabase_client()
    if not client:
        return 0
    try:
        import datetime
        cutoff_date = (datetime.date.today() - datetime.timedelta(days=days_retention)).isoformat()
        res = client.table("daily_reports").delete().lt("report_date", cutoff_date).execute()
        count = len(res.data) if res.data else 0
        if count > 0:
            logger.info(f"Purge automatique Supabase : {count} rapport(s) antérieur(s) au {cutoff_date} supprimé(s).")
        return count
    except Exception as err:
        logger.debug(f"Avertissement lors de la purge automatique Supabase : {err}")
        return 0


def get_available_dates() -> List[str]:
    """Récupère la liste de toutes les dates de rapports disponibles, triées par date décroissante."""
    dates: List[str] = []
    client = get_supabase_client()
    if client:
        try:
            res = (
                client.table("daily_reports")
                .select("report_date")
                .order("report_date", desc=True)
                .execute()
            )
            dates = [row["report_date"] for row in (res.data or []) if "report_date" in row]
        except Exception as e:
            logger.debug(f"Erreur lors de la récupération des dates disponibles : {e}")

    # Fallback local transparent : intègre la date du cache local si disponible
    local_cache_path = os.path.join(os.path.dirname(__file__), "latest_report.json")
    if os.path.exists(local_cache_path):
        try:
            with open(local_cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                cached_date = cached_data.get("report_date")
                if cached_date and cached_date not in dates:
                    dates.insert(0, cached_date)
        except Exception:
            pass

    return dates


def get_report_by_date(report_date: str) -> Optional[Dict[str, Any]]:
    """Récupère le rapport correspondant à une date spécifique."""
    client = get_supabase_client()
    if client:
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
        except Exception as e:
            logger.debug(f"Erreur lors de la récupération du rapport {report_date} : {e}")

    # Fallback sur le cache local latest_report.json
    local_cache_path = os.path.join(os.path.dirname(__file__), "latest_report.json")
    if os.path.exists(local_cache_path):
        try:
            with open(local_cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                if cached_data.get("report_date") == report_date or not report_date:
                    return {
                        "report_date": cached_data.get("report_date", report_date),
                        "raw_summary": cached_data,
                    }
        except Exception:
            pass

    return None


def get_latest_report() -> Optional[Dict[str, Any]]:
    """Récupère le rapport le plus récent présent dans la base ou en cache local."""
    client = get_supabase_client()
    if client:
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
        except Exception as e:
            logger.debug(f"Erreur lors de la récupération du dernier rapport : {e}")

    local_cache_path = os.path.join(os.path.dirname(__file__), "latest_report.json")
    if os.path.exists(local_cache_path):
        try:
            with open(local_cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                return {
                    "report_date": cached_data.get("report_date"),
                    "raw_summary": cached_data,
                }
        except Exception:
            pass

    return None
