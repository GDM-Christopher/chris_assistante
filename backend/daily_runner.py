#!/usr/bin/env python3
"""Backend Runner Quotidien - Ingestion, Analyse IA (Gemini 1.5 Pro) & Stockage Supabase.

Usage :
    python backend/daily_runner.py
    python backend/daily_runner.py --mock
    python backend/daily_runner.py --dry-run
    python backend/daily_runner.py --sample-upload
    python backend/daily_runner.py --date 2026-09-20
"""

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Garantir que la racine du projet est présente dans sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.chat_client import fetch_recent_chat_messages
from backend.config import GMAIL_LABELS_FILTER, GMAIL_LOOKBACK_HOURS
from backend.gemini_analyzer import analyze_daily_communications
from backend.gmail_client import fetch_recent_emails
from backend.google_auth import get_google_credentials
from backend.mock_data import MOCK_STRUCTURED_SUMMARY, MOCK_SUPERVISION_MESSAGES
from backend.supabase_client import upsert_daily_report

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DailyRunner")


def run_pipeline(
    target_date: str,
    mock_mode: bool = False,
    dry_run: bool = False,
    sample_upload: bool = False,
    hours: int = 24,
) -> bool:
    """Exécute la chaîne complète : Ingestion Google -> Gemini 1.5 Pro -> Supabase."""
    logger.info("=" * 70)
    logger.info(f"DÉMARRAGE DU RUNNER QUOTIDIEN POUR LA DATE : {target_date}")
    logger.info(f"Options : Mock={mock_mode}, DryRun={dry_run}, SampleUpload={sample_upload}, Lookback={hours}h")
    logger.info("=" * 70)

    # 1. Mode Raccourci : Sample Upload (Injecte un jeu de données complet dans Supabase)
    if sample_upload:
        logger.info("Mode --sample-upload activé : Injection directe du jeu de test dans Supabase.")
        if dry_run:
            print(json.dumps(MOCK_STRUCTURED_SUMMARY, indent=2, ensure_ascii=False))
            return True
        success = upsert_daily_report(target_date, MOCK_STRUCTURED_SUMMARY)
        logger.info(f"Résultat de l'insertion Supabase : {'SUCCÈS' if success else 'ÉCHEC'}")
        return success

    raw_messages: List[Dict[str, Any]] = []

    # 2. Ingestion des données (Mode Mock ou Réel Google Workspace)
    if mock_mode:
        logger.info("Mode --mock activé : Utilisation des messages de simulation DSI/OneStock/OPCON.")
        raw_messages = MOCK_SUPERVISION_MESSAGES
    else:
        logger.info("Connexion aux APIs Google Workspace...")
        creds = get_google_credentials()
        if not creds:
            logger.warning(
                "Aucun identifiant Google Workspace valide détecté. "
                "Bascule automatique en mode données simulées (--mock) pour poursuivre l'analyse..."
            )
            raw_messages = MOCK_SUPERVISION_MESSAGES
        else:
            # Récupération Gmail
            gmail_messages = fetch_recent_emails(
                creds, hours=hours, labels=GMAIL_LABELS_FILTER
            )
            raw_messages.extend(gmail_messages)

            # Récupération Google Chat
            chat_messages = fetch_recent_chat_messages(creds, hours=hours)
            raw_messages.extend(chat_messages)

    logger.info(f"Total de {len(raw_messages)} messages bruts collectés.")

    if not raw_messages:
        logger.warning(
            "Aucun message technique collecté sur les dernières 24h. "
            "Création d'un rapport nominal automatique."
        )
        summary = {
            "statut_global": "Vert",
            "resume_executif": f"Aucun incident ni alerte technique répertorié pour le {target_date}.",
            "alertes": [],
            "incidents": [],
            "projets": [],
        }
    else:
        # 3. Analyse via Gemini 1.5 Pro
        logger.info("Envoi des messages à Gemini 1.5 Pro pour extraction structurée...")
        try:
            summary = analyze_daily_communications(raw_messages, date_str=target_date)
        except Exception as e:
            logger.error(f"Erreur d'analyse Gemini : {e}")
            if mock_mode:
                logger.info("Utilisation du résumé de repli simulé...")
                summary = MOCK_STRUCTURED_SUMMARY
            else:
                raise e

    # 4. Affichage ou Stockage Supabase
    logger.info(f"Synthèse IA générée : Statut={summary.get('statut_global')}, "
                f"Alertes={len(summary.get('alertes', []))}, "
                f"Incidents={len(summary.get('incidents', []))}, "
                f"Projets={len(summary.get('projets', []))}")

    # Sauvegarde locale automatique en cache (permet un affichage immédiat dans Streamlit)
    try:
        cache_path = PROJECT_ROOT / "backend" / "latest_report.json"
        payload_to_cache = {"report_date": target_date, **summary}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload_to_cache, f, indent=2, ensure_ascii=False)
        logger.info(f"Rapport sauvegardé localement en cache dans : {cache_path}")
    except Exception as cache_err:
        logger.warning(f"Avertissement cache local : {cache_err}")

    if dry_run:
        logger.info("Mode --dry-run activé : Aucune écriture dans Supabase. Résultat ci-dessous :")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return True

    # 5. Persistance Supabase
    try:
        upsert_daily_report(target_date, summary)
        logger.info("✅ Pipeline exécuté avec succès. Données disponibles dans Streamlit !")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde dans Supabase : {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Runner Quotidien de Supervision Technique IA")
    today_str = datetime.date.today().isoformat()
    parser.add_argument(
        "--date",
        type=str,
        default=today_str,
        help=f"Date du rapport au format YYYY-MM-DD (défaut : aujourd'hui {today_str})",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Utilise un jeu de messages de supervision simulés au lieu d'appeler les APIs Google",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le JSON extrait sans insérer dans Supabase",
    )
    parser.add_argument(
        "--sample-upload",
        action="store_true",
        help="Insère immédiatement un rapport de démonstration complet dans Supabase",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=GMAIL_LOOKBACK_HOURS,
        help="Période d'historique en heures (défaut : 24h)",
    )

    args = parser.parse_args()

    success = run_pipeline(
        target_date=args.date,
        mock_mode=args.mock,
        dry_run=args.dry_run,
        sample_upload=args.sample_upload,
        hours=args.hours,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
