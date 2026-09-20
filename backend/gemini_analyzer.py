"""Module d'analyse IA avec Gemini 1.5 Pro via le SDK officiel google-genai."""

import json
import logging
import re
from typing import Any, Dict, List, Literal, Optional

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
    source_type: Optional[str] = Field(
        default="Gmail",
        description="Type de source : 'Gmail' ou 'Google Chat'"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Lien URL direct vers l'e-mail ou message source pour consultation immédiate"
    )
    source_ref: Optional[str] = Field(
        default=None,
        description="Référence courte (ex: nom de l'expéditeur ou sujet du message source)"
    )


class ProjetModel(BaseModel):
    nom_projet: str = Field(description="Nom usuel du projet ou domaine concerné")
    libelle: str = Field(description="Libellé ou tag source (ex: Snowflake, OneStock, Notification_DSI, OPCON, Stambia)")
    actions_realisees: List[str] = Field(
        default_factory=list,
        description="Liste concrète des actions achevées ou avancées au cours des dernières 24h"
    )
    decisions: List[str] = Field(
        default_factory=list,
        description="Liste des décisions prises, arbitrages ou prochaines étapes validées"
    )
    source_type: Optional[str] = Field(
        default="Gmail",
        description="Type de source : 'Gmail' ou 'Google Chat'"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Lien URL direct vers l'e-mail ou message source pour consultation immédiate"
    )
    source_ref: Optional[str] = Field(
        default=None,
        description="Auteur principal ou sujet de l'échange (ex: Sylvain Cursoux, Annette Vandamme)"
    )


class ReunionModel(BaseModel):
    titre: str = Field(description="Titre de la réunion")
    date_heure: str = Field(description="Date et créneau horaire de la réunion")
    organisateur: str = Field(default="Inconnu", description="Organisateur ou émetteur de la réunion")
    participants: List[str] = Field(default_factory=list, description="Liste des participants ou équipes concernées")
    sujets_abordes: List[str] = Field(default_factory=list, description="Ordre du jour ou sujets clés à aborder")
    ce_que_je_dois_preparer: List[str] = Field(
        default_factory=list,
        description="Actions concrètes, indicateurs, dossiers ou arbitrages que Christopher doit préparer pour cette réunion"
    )
    contexte_emails_chats: str = Field(
        default="",
        description="Synthèse du contexte récent (incidents en cours, projets, décisions de Sylvain, Annette ou équipe) en lien direct avec cette réunion"
    )
    source_type: Optional[str] = Field(default="Gmail", description="'Gmail' ou 'Google Calendar'")
    source_url: Optional[str] = Field(default=None, description="Lien direct pour ouvrir l'invitation ou l'événement")
    source_ref: Optional[str] = Field(default=None, description="Référence ou expéditeur de l'invitation")


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
    reunions_a_venir: List[ReunionModel] = Field(
        default_factory=list,
        description="Réunions à venir, sujets clés et préparation sur-mesure pour Christopher"
    )


# --- System Prompt Gemini ---

SYSTEM_PROMPT = """Tu es un Architecte Cloud, Directeur Technique Adjoint et Superviseur DSI expérimenté.
Tu reçois l'ENSEMBLE des flux et e-mails récents de la boîte de réception (Gmail), des salons Google Chat des dernières 24 à 48 heures, ainsi que les INVITATIONS ET AGENDAS DE RÉUNIONS À VENIR, SANS AUCUN FILTRE PRÉALABLE.

Ton rôle est d'effectuer le TRI INTELLIGENT DE MANIÈRE TOTALEMENT AUTONOME :

1. CE QUE TU DOIS IGNORER (LE BRUIT) :
   - Les spams, publicités, newsletters commerciales, notifications d'outils marketing.
   - Les réponses automatiques de présence d'agenda (ex: "X a accepté la réunion").
   - Les annonces RH génériques, félicitations, ou échanges informels sans portée technique ou projet.

2. CE QUE TU DOIS CAPTURER, ANALYSER ET STRUCTURER :
   - ALERTES & INCIDENTS TECHNIQUES :
     * Pannes, rejets de batchs, jobs en échec, erreurs d'API (OneStock, Stambia, OPCON, NODHOS, Logys, bases de données, etc.).
     * Identifier précisément : titre, description, bdd_impactees, flux_impactes, cause_racine, solution_technique, statut ("Résolu" ou "En cours").
   - PROJETS, CHANTIERS APPLICATIFS & DÉCISIONS :
     * Tout échange projet ou métier structurant (ex: Proposition d'Implantation, WinWig, Snowflake, ERP, Supply Chain, Réassort, etc.).
     * Les retours d'équipes et arbitrages (ex: Sylvain Cursoux, Annette Vandamme, Christopher Gilleron, Marie Ducorney, prestataires).
     * Isole clairement dans chaque projet : nom_projet, libelle, actions_realisees (ce qui a été livré ou testé), decisions (ce qui est décidé, les priorités fixées ou les points de passation).
   - ALERTES MAJEURES & RISQUES :
     * Retards de livraison, bugs d'ingestion (ex: problème de propagation WinWig -> Snowflake), blocages de stocks ou de commandes.
   - STATUT GLOBAL DU SI :
     * 'Vert' si tout est nominal ou incidents mineurs clos.
     * 'Orange' si des flux sont dégradés ou incidents/anomalies projet en cours sans arrêt total.
     * 'Rouge' si un blocage critique paralyse l'activité (magasins, entrepôt, e-commerce).

3. RÉUNIONS À VENIR & CE QUE CHRISTOPHER DOIT PRÉPARER (POINT CRUCIAL) :
   - Identifie toutes les réunions professionnelles à venir (ex: Hebdo - Data/IA - Supply avec Marie Ducorney, points de run, cadrages projets).
   - Pour chacune d'elles :
     * titre : Nom clair de la réunion.
     * date_heure : Date et créneau horaire exacts.
     * organisateur : Personne ayant convoqué ou pilotant la réunion.
     * participants : Personnes conviées.
     * sujets_abordes : Ordre du jour et thématiques abordées.
     * ce_que_je_dois_preparer : Liste très concrète des actions, chiffres à connaître, dossiers ou arbitrages que Christopher Gilleron doit avoir préparés avant la réunion (ex: statut de la MEP du stock mini magasin, point d'ingestion WinWig -> Snowflake, réponse à apporter à la règle Annette sur la référence H26ABI.T rouge).
     * contexte_emails_chats : Résumé synthétique de tous les éléments extraits des e-mails et chats récents en rapport avec les thèmes de cette réunion pour donner à Christopher tout le contexte d'un coup d'œil.
     * source_url : Lien direct vers l'invitation ou l'e-mail source.
     * source_ref : Nom de l'émetteur.

4. TRAÇABILITÉ DES SOURCES :
   - Pour CHAQUE incident, CHAQUE projet et CHAQUE réunion, renseigne impérativement :
     * source_type : 'Gmail' ou 'Google Chat' ou 'Google Calendar'.
     * source_url : Copie EXACTEMENT l'URL fournie dans le header du message correspondant ('Lien direct: ...').
     * source_ref : Nom de l'expéditeur ou titre du fil.

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
    meetings_payload: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Analyse les messages bruts et réunions via Gemini et renvoie un dictionnaire structuré."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY est manquante dans les variables d'environnement. "
            "Veuillez définir votre clé dans le fichier .env ou les secrets GitHub."
        )

    logger.info(f"Initialisation de l'analyse Gemini pour le {date_str}...")

    # Formatage du contexte textuel pour le prompt avec lien source
    formatted_context = []
    for idx, item in enumerate(messages_payload, start=1):
        src = item.get("source", "Source")
        sender = item.get("expediteur", "Inconnu")
        date_item = item.get("date", "")
        sujet = item.get("sujet", item.get("espace", "N/A"))
        content = item.get("contenu", item.get("message", ""))
        url = item.get("url", "")

        formatted_context.append(
            f"--- [Message #{idx} | {src} | Date: {date_item} | Lien direct: {url}] ---\n"
            f"De : {sender}\n"
            f"Sujet / Salon : {sujet}\n"
            f"Contenu :\n{content}\n"
        )

    full_text_input = "\n\n".join(formatted_context)

    # Ajout du bloc Réunions & Invitations
    if meetings_payload:
        formatted_meetings = []
        for idx, m in enumerate(meetings_payload, start=1):
            src = m.get("source", "Calendrier")
            sender = m.get("expediteur") or m.get("organisateur", "Inconnu")
            date_m = m.get("date_heure") or m.get("date", "")
            sujet = m.get("sujet", "Réunion")
            content = m.get("contenu", "")
            url = m.get("url", "")

            formatted_meetings.append(
                f"--- [Invitation Réunion #{idx} | {src} | Date/Heure: {date_m} | Lien direct: {url}] ---\n"
                f"De / Organisateur : {sender}\n"
                f"Titre / Objet : {sujet}\n"
                f"Détails / Description :\n{content}\n"
            )
        full_text_input += (
            "\n\n=================================================================\n"
            "=== INVITATIONS ET AGENDAS DES RÉUNIONS À VENIR ===\n"
            "=================================================================\n\n"
            + "\n\n".join(formatted_meetings)
        )

    user_prompt = (
        f"Date du rapport : {date_str}\n\n"
        f"Voici l'ensemble des échanges, alertes, projets récents et réunions à venir :\n\n"
        f"{full_text_input}"
    )

    try:
        # Initialisation du client officiel Google GenAI
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        # Liste ordonnée de modèles candidats compatibles
        candidate_models = [GEMINI_MODEL, "gemini-2.5-flash", "gemini-flash-latest"]
        models_to_try = []
        for m in candidate_models:
            if m and m not in models_to_try:
                models_to_try.append(m)

        response = None
        last_error = None

        for model_name in models_to_try:
            try:
                logger.info(f"Tentative d'analyse IA avec le modèle {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=DailySummaryModel,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    logger.info(f"Réponse obtenue avec succès via {model_name}.")
                    break
            except Exception as model_err:
                logger.warning(f"Échec de l'appel avec le modèle {model_name} : {model_err}")
                last_error = model_err

        if not response or not response.text:
            if last_error:
                raise last_error
            raise RuntimeError("Aucune réponse générée par l'API Gemini.")

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
