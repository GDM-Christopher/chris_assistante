"""Jeu de données simulées réalistes pour tester en local le pipeline sans identifiants Google."""

from typing import Any, Dict, List

MOCK_SUPERVISION_MESSAGES: List[Dict[str, Any]] = [
    {
        "source": "Gmail",
        "id": "mock_gmail_01",
        "date": "2026-09-20 04:15:22",
        "expediteur": "alerte-opcon@supervision.entreprise.com",
        "sujet": "[OPCON][CRITIQUE] Échec job nocturne trt_stambia_nodhos_stocks",
        "extrait": "Le job OPCON #8841 a échoué sur le serveur PROD-ETL01. Erreur SQL ORA-00001: unique constraint violated.",
        "contenu": """Bonjour,
Le job OPCON #8841 (flux trt_stambia_nodhos_stocks) s'est arrêté en statut ABEND à 04:12 UTC.
Serveur : PROD-ETL01
Base cible : NODHOS_DB (schéma GDM_STOCK)
Message d'erreur :
ORA-00001: unique constraint (GDM_STOCK.PK_STOCK_MAGASIN) violated
Le traitement des stocks magasins NODHOS n'a pas pu s'achever. Les 420 magasins risquent d'afficher des stocks obsolètes à l'ouverture à 08h30 si aucune action corrective n'est menée.
Astreinte prévenue.""",
    },
    {
        "source": "Gmail",
        "id": "mock_gmail_02",
        "date": "2026-09-20 06:45:10",
        "expediteur": "support-onestock@onestock-retail.com",
        "sujet": "[OneStock via RUN] Alerte latence et retards sur le flux de synchronisation des commandes",
        "extrait": "SLA d'ingestion des commandes dépassé (> 45 minutes) entre OneStock OMS et l'ERP PROD_COMMERCE.",
        "contenu": """Alerte Supervision OneStock via RUN :
Date : 2026-09-20 à 06:40:00
Depuis 05h15, le connecteur API OneStock vers votre base PROD_COMMERCE subit une congestion.
Le temps de réponse moyen de l'endpoint /api/v2/orders/sync est passé de 250ms à 3800ms.
File d'attente actuelle : 1 420 commandes en attente d'acquittement.
Impact : Les commandes web risquent de ne pas être visibles en temps voulu pour la préparation magasin ce matin.
Merci de vérifier la disponibilité du serveur reverse-proxy et les verrous de table sur PROD_COMMERCE.""",
    },
    {
        "source": "Gmail",
        "id": "mock_gmail_03",
        "date": "2026-09-20 07:15:00",
        "expediteur": "dsi-infra@entreprise.com",
        "sujet": "[Notification_DSI] Maintenance planifiée réseau et switchs de cœur de salle",
        "extrait": "Intervention réseau programmée le 20/09 de 22h00 à 23h30. Risque de micro-coupures sur les flux BDD.",
        "contenu": """Chers collègues de la DSI,
Une intervention réseau est planifiée ce soir jeudi de 22h00 à 23h30 pour mise à jour du firmware des switchs de production.
Impacts attendus :
- Deux micro-coupures de 30 secondes max sur les connexions inter-sites.
- Les flux Stambia et batchs OPCON prévus entre 22h00 et 23h30 doivent être mis en pause ou décalés après 23h45.
Merci d'adapter vos ordonnancements.""",
    },
    {
        "source": "Google Chat",
        "espace": "DSI - Incidents & Run Technique",
        "date": "2026-09-20 06:30:15",
        "expediteur": "Alexandre (Ingénieur Data/DBA)",
        "message": "Update sur l'échec OPCON trt_stambia : c'était un doublon d'article envoyé lors du catalogue de minuit. J'ai exécuté le script SQL de nettoyage de la staging table, ajusté la clause MERGE INTO dans le script Stambia et relancé le job OPCON. Tout est repassé au VERT à 06h28, les stocks NODHOS sont à jour pour l'ouverture !",
    },
    {
        "source": "Google Chat",
        "espace": "Projet OneStock & Omnicanal",
        "date": "2026-09-20 08:10:45",
        "expediteur": "Sophie (Tech Lead Intégration)",
        "message": "Concernant l'alerte OneStock via RUN : le pool de connexion du proxy avait saturé suite au pic de promo. On a augmenté max_connections à 250 et redémarré le service. La file d'attente de 1420 commandes a été totalement dépilée en 20 min. En réunion projet ce matin avec l'équipe OneStock, nous avons validé la bascule vers des Webhooks d'ici fin Q3 pour éviter ce genre de goulet d'étranglement batch.",
    },
]

MOCK_STRUCTURED_SUMMARY: Dict[str, Any] = {
    "statut_global": "Orange",
    "resume_executif": "Matinée marquée par un échec du flux Stambia sur NODHOS et un ralentissement d'ingestion OneStock consécutif à une saturation de pool de connexions. Les deux incidents ont été diagnostiqués et résolus avec succès avant l'ouverture des magasins. Les flux sont à présent nominaux.",
    "alertes": [
        "Retard temporaire d'ingestion des commandes OneStock (> 45 min de délai d'acquittement, résolu à 08h00)",
        "Intervention de maintenance réseau DSI planifiée ce soir de 22h00 à 23h30 (impact possible sur les batchs nocturnes)",
        "Surveillance renforcée recommandée sur la table GDM_STOCK de NODHOS suite au doublon de catalogue"
    ],
    "incidents": [
        {
            "titre": "Échec du job nocturne Stambia trt_stambia_nodhos_stocks",
            "description": "Arrêt brutal du flux de valorisation des stocks magasins avec code erreur ORA-00001 (violation de contrainte unique) sur la base NODHOS.",
            "bdd_impactees": ["NODHOS_DB", "GDM_STOCK"],
            "flux_impactes": ["trt_stambia_nodhos_stocks", "OPCON_Job_8841"],
            "cause_racine": "Doublon de matricule article transmis lors de l'import de catalogue de minuit.",
            "solution_technique": "Exécution d'un script SQL de dédoublonnage préalable, modification du mapping Stambia avec MERGE INTO et relance manuelle du job OPCON (validé à 06h28).",
            "statut": "Résolu"
        },
        {
            "titre": "Congestion et latence critique du connecteur OneStock",
            "description": "File d'attente de 1 420 commandes bloquées avec temps de réponse dégradé à 3 800ms sur l'API de commande.",
            "bdd_impactees": ["PROD_COMMERCE"],
            "flux_impactes": ["OneStock via RUN", "Flux_Orders_Sync"],
            "cause_racine": "Pool de connexions saturated sur le reverse-proxy sous l'effet du pic nocturne de commandes promotionnelles.",
            "solution_technique": "Élévation de la directive max_connections à 250 sur le proxy, redémarrage du service d'ingestion et résorption complète de la file en 20 minutes.",
            "statut": "Résolu"
        },
        {
            "titre": "Latence résiduelle sur les requêtes de consultation stock OMS",
            "description": "Quelques timeouts intermittents constatés lors des appels de vérification de disponibilité en point de vente.",
            "bdd_impactees": ["PROD_COMMERCE", "NODHOS_DB"],
            "flux_impactes": ["Flux_Stock_Lookup"],
            "cause_racine": "Index manquant sur la colonne de date de mise à jour des stocks suite au patch applicatif.",
            "solution_technique": "Script de création d'index concurrentiel (CREATE INDEX CONCURRENTLY) prêt, planifié pour application lors du créneau de maintenance de 22h.",
            "statut": "En cours"
        }
    ],
    "projets": [
        {
            "nom_projet": "Refonte Omnicanale OneStock",
            "libelle": "OneStock via RUN",
            "actions_realisees": [
                "Purge et dépilage de la file d'attente de 1420 commandes web",
                "Augmentation du seuil des pools de connexions sur les serveurs frontaux",
                "Revue de dimensionnement des capacités d'ingestion"
            ],
            "decisions": [
                "Bascule définitive vers l'architecture événementielle Webhooks OneStock d'ici la fin du 3ème trimestre",
                "Ajout d'un contrôle automatique de saturation de file dans la supervision Datadog/Prometheus"
            ]
        },
        {
            "nom_projet": "Ordonnancement & Flux ETL Stambia / OPCON",
            "libelle": "Notification_DSI / OPCON",
            "actions_realisees": [
                "Dépannage à chaud du job OPCON 8841 avec dédoublonnage SQL",
                "Adaptation du script de mapping Stambia pour gérer nativement les doublons de clés",
                "Notification aux équipes magasins confirmant la conformité des stocks à l'ouverture"
            ],
            "decisions": [
                "Planification du gel des jobs batchs entre 22h00 et 23h30 ce soir en raison de la maintenance réseau DSI",
                "Audit prévu de la qualité des données transmises par le fichier source catalogue amont"
            ]
        }
    ]
}
