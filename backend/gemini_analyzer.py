"""Module d'analyse IA avec Gemini 1.5 Pro via le SDK officiel google-genai."""

import json
import logging
import re
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from backend.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("GeminiAnalyzer")


# --- Modèles Pydantic pour validation stricte du schéma ---

class IncidentModel(BaseModel):
    titre: str = Field(description="Titre court et explicite de l'incident")
    description: str = Field(description="Description synthétique de l'anomalie constatée")
    bdd_impactees: List[str] = Field(
        default_factory=list,
        description="Liste des bases de données ou tables impactées (ex: NODHOS, PROD_COMMERCE, ORACLE_STOCK)"
    )
    flux_impactes: List[str] = Field(
        default_factory=list,
        description="Liste des flux ou batchs impactés (ex: OneStock via RUN, OPCON, trt_stambia)"
    )
    cause_racine: str = Field(description="Cause racine identifiée de l'incident ou hypothèse principale")
    solution_technique: str = Field(
        description="Solution technique appliquée ou action corrective préconisée"
    )
    statut: Literal["Résolu", "En cours"] = Field(
        default="En cours",
        description="Statut actuel de l'incident : 'Résolu' ou 'En cours'"
    )


class ProjetModel(BaseModel):
    nom_projet: str = Field(description="Nom usuel du projet ou domaine concerné")
    libelle: str = Field(description="Libellé ou tag source (ex: OneStock, Notification_DSI, OPCON, Stambia)")
    actions_realisees: List[str] = Field(
        default_factory=list,
        description="Liste concrète des actions achevées ou avancées au cours des dernières 24h"
    )
    decisions: List[str] = Field(
        default_factory=list,
        description="Liste des décisions prises, arbitrages ou prochaines étapes validées"
    )


class DailySummaryModel(BaseModel):
    statut_global: Literal["Vert", "Orange", "Rouge"] = Field(
        default="Vert",
        description="Indicateur de santé globale du SI : 'Vert' (nominal), 'Orange' (dégradé/alertes), 'Rouge' (critique/bloquant)"
    )
    resume_executif: str = Field(
        description="Synthèse exécutive en 2-4 phrases résumant l'activité technique de la journée"
    )
    alertes: List[str] = Field(
        default_factory=list,
        description="Liste des alertes majeures, retards SLA ou risques critiques détectés"
    )
    incidents: List[IncidentModel] = Field(
        default_factory=list,
        description="Liste des incidents techniques répertoriés"
    )
    projets: List[ProjetModel] = Field(
        default_factory=list,
        description="Avancement et décisions par projet"
    )


# --- System Prompt Gemini ---

SYSTEM_PROMPT = """Tu es un Architecte Cloud, Ingénieur Software Full-Stack et Superviseur Technique de haut niveau.
Ton rôle est d'analyser l'ensemble des flux techniques (e-mails Gmail de supervision DSI, jobs OPCON, flux Stambia, notifications OneStock, alertes de bases de données, et messages Google Chat) reçus au cours des dernières 24 heures.

À partir des messages bruts fournis, tu dois extraire et structurer l'information de manière rigoureuse selon les règles suivantes :

1. ALERTES :
   - Identifie tous les points de vigilance, les retards de SLA, les seuils critiques atteints ou les interventions planifiées.
   
2. INCIDENTS :
   - Pour chaque dysfonctionnement, panne de flux, échec de job ou erreur applicative :
     * titre : Nom clair et technique de l'incident.
     * description : Ce qui s'est passé concrètement.
     * bdd_impactees : Liste des bases ou schémas (ex: NODHOS, PROD_COMMERCE, ORACLE_STOCKS, etc.).
     * flux_impactes : Nom exact du flux ou job (ex: OneStock via RUN, OPCON, trt_stambia, etc.).
     * cause_racine : Explication technique précise de la cause (saturations, verrous, erreurs de code, clés dupliquées).
     * solution_technique : Détail précis de la résolution (script SQL, relance de job, reparamétrage).
     * statut : 'Résolu' si l'incident est clos/corrigé, 'En cours' s'il nécessite encore des actions.

3. PROJETS & ÉVOLUTIONS :
   - Regroupe les actions menées et décisions par projet ou libellé technique (OneStock, DSI, Stambia/OPCON, etc.).
   - Isole clairement les décisions prises et les prochains jalons.

4. STATUT GLOBAL :
   - 'Vert' si tous les flux sont nominaux ou les incidents mineurs résolus.
   - 'Orange' si des flux sont dégradés ou des incidents en cours sans impact bloquant majeur.
   - 'Rouge' si un flux critique ou une BDD de production est indisponible.

Réponds STRICTEMENT au format JSON valide conforme au schéma imposé. Aucun texte introductif, aucune explication hors du JSON.
"""


def clean_json_response(raw_text: str) -> str:
    """Retire les balises markdown ```json ... ``` si présentes."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def analyze_daily_communications(
    messages_payload: List[Dict[str, Any]],
    date_str: str,
) -> Dict[str, Any]:
    """Analyse les messages bruts via Gemini 1.5 Pro et renvoie un dictionnaire structuré."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY est manquante dans les variables d'environnement. "
            "Veuillez définir votre clé dans le fichier .env ou les secrets GitHub."
        )

    logger.info(f"Initialisation de l'analyse Gemini 1.5 Pro pour le {date_str}...")

    # Formatage du contexte textuel pour le prompt
    formatted_context = []
    for idx, item in enumerate(messages_payload, start=1):
        src = item.get("source", "Source")
        sender = item.get("expediteur", "Inconnu")
        date_item = item.get("date", "")
        sujet = item.get("sujet", item.get("espace", "N/A"))
        content = item.get("contenu", item.get("message", ""))

        formatted_context.append(
            f"--- [Message #{idx} | {src} | {date_item}] ---\n"
            f"De : {sender}\n"
            f"Sujet / Espace : {sujet}\n"
            f"Contenu :\n{content}\n"
        )

    full_text_input = "\n\n".join(formatted_context)
    user_prompt = f"Date du rapport : {date_str}\n\nVoici les échanges et alertes techniques des dernières 24 heures :\n\n{full_text_input}"

    try:
        # Initialisation du client officiel Google GenAI
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=DailySummaryModel,
                temperature=0.2,
            ),
        )

        response_text = response.text
        cleaned = clean_json_response(response_text)
        data = json.loads(cleaned)

        # Validation par le modèle Pydantic
        validated = DailySummaryModel(**data)
        logger.info(
            f"Analyse terminée avec succès : {len(validated.incidents)} incidents, "
            f"{len(validated.alertes)} alertes, {len(validated.projets)} projets."
        )
        return validated.model_dump()

    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API Gemini : {e}")
        # Tentative de repli si le SDK a renvoyé un texte non validé directement
        try:
            if 'response_text' in locals() and response_text:
                cleaned = clean_json_response(response_text)
                data = json.loads(cleaned)
                return data
        except Exception:
            pass
        raise e
