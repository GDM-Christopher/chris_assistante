-- ==============================================================================
-- SCHEMA SUPABASE : Table de supervision technique quotidienne (daily_reports)
-- Description : Stocke les synthèses quotidiennes générées par Gemini 1.5 Pro
--               après ingestion des e-mails Gmail et échanges Google Chat.
-- ==============================================================================

-- 1. Activation de l'extension pgcrypto (si non active) pour générer les UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Création de la table principale
CREATE TABLE IF NOT EXISTS public.daily_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE NOT NULL UNIQUE,
    raw_summary JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Création des index de performance
-- Index B-Tree sur la date du rapport (recherche et tri chronologique descendant)
CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON public.daily_reports (report_date DESC);

-- Index GIN sur le contenu JSONB pour accélérer les filtres et recherches plein texte
CREATE INDEX IF NOT EXISTS idx_daily_reports_raw_summary ON public.daily_reports USING gin (raw_summary);

-- 4. Fonction et déclencheur automatique pour 'updated_at'
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_daily_reports_updated_at ON public.daily_reports;
CREATE TRIGGER tr_daily_reports_updated_at
    BEFORE UPDATE ON public.daily_reports
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 5. Sécurité et Politiques RLS (Row Level Security)
ALTER TABLE public.daily_reports ENABLE ROW LEVEL SECURITY;

-- Autoriser la lecture publique ou aux utilisateurs authentifiés pour le dashboard Streamlit
CREATE POLICY "Permettre la lecture des rapports pour tous"
    ON public.daily_reports
    FOR SELECT
    USING (true);

-- Autoriser l'insertion et la mise à jour pour le rôle de service (backend / GitHub Actions)
CREATE POLICY "Permettre l'insertion/mise à jour pour la clé service"
    ON public.daily_reports
    FOR ALL
    USING (auth.role() = 'service_role' OR auth.role() = 'anon')
    WITH CHECK (auth.role() = 'service_role' OR auth.role() = 'anon');

-- ==============================================================================
-- 6. JEU DE DONNÉES DE DÉMONSTRATION (Optionnel - pour tester immédiatement le dashboard)
-- ==============================================================================
INSERT INTO public.daily_reports (report_date, raw_summary)
VALUES (
    CURRENT_DATE,
    '{
        "statut_global": "Orange",
        "resume_executif": "Activité marquée par des ralentissements sur les flux OneStock et un blocage temporaire d''intégration Stambia sur la base NODHOS. Deux incidents majeurs pris en charge et résolus avec succès.",
        "alertes": [
            "Retard de synchronisation détecté sur le flux d''inventaire OneStock (dépassant 45 min de SLA)",
            "Erreur de contrainte d''intégrité sur la table de staging STG_ARTICLES lors de l''exécution OPCON de 04h00",
            "Maintenance planifiée sur l''infrastructure réseau DSI prévue ce soir à 22h00"
        ],
        "incidents": [
            {
                "titre": "Blocage du flux d''intégration des commandes OneStock",
                "description": "L''ingestion des commandes via l''API OneStock était en échec suite à un timeout réseau vers le serveur de production.",
                "bdd_impactees": ["PROD_COMMERCE", "NODHOS_DB"],
                "flux_impactes": ["Flux_OneStock_Orders_In", "Flux_ERP_Sync"],
                "cause_racine": "Pool de connexions saturé sur le reverse-proxy après un pic de commandes promotionnelles nocturnes.",
                "solution_technique": "Augmentation de max_connections à 250 sur le pool de connexion et redémarrage propre du service d''ingestion avec purge de la file d''attente bloquante.",
                "statut": "Résolu"
            },
            {
                "titre": "Échec du job Stambia trt_stambia_nodhos_stocks",
                "description": "Le traitement d''actualisation des stocks magasins s''est interrompu avec le code erreur SQL ORA-00001 (clé dupliquée).",
                "bdd_impactees": ["NODHOS_DB", "STOCK_DATAMART"],
                "flux_impactes": ["trt_stambia_stocks", "Flux_Stambia_ETL"],
                "cause_racine": "Doublon de matricule article généré lors de la migration du catalogue de minuit.",
                "solution_technique": "Exécution d''un script SQL de dédoublonnage préalable, ajout d''une clause MERGE INTO dans le mapping Stambia et relance manuelle du job OPCON (statut OK à 06h30).",
                "statut": "Résolu"
            },
            {
                "titre": "Latence anormale sur les requêtes d''inventaire temps réel",
                "description": "Temps de réponse supérieur à 4 secondes constaté sur les endpoints de consultation de stock en magasin.",
                "bdd_impactees": ["PROD_COMMERCE"],
                "flux_impactes": ["Flux_Stock_Lookup"],
                "cause_racine": "Index manquant sur la colonne last_stock_update_ts suite au dernier déploiement de patch.",
                "solution_technique": "Analyse du plan d''exécution (EXPLAIN ANALYZE) et création d''un index concurrentiel en cours de validation sur l''environnement de pré-production.",
                "statut": "En cours"
            }
        ],
        "projets": [
            {
                "nom_projet": "Refonte Intégration OneStock",
                "libelle": "OneStock via RUN",
                "actions_realisees": [
                    "Audit des logs d''erreurs des 7 derniers jours sur le flux de confirmation d''expédition",
                    "Mise en place de métriques Prometheus pour suivre le temps de réponse de l''API",
                    "Validation du format JSON v2 avec l''équipe partenaire"
                ],
                "decisions": [
                    "Bascule du mode d''ingestion par lot (batch) vers un mode événementiel par Webhooks d''ici fin Q3",
                    "Augmentation du seuil d''alerte critique de 30s à 45s pendant la période de soldes"
                ]
            },
            {
                "nom_projet": "Modernisation de la chaîne ETL Stambia & OPCON",
                "libelle": "Notification_DSI / OPCON",
                "actions_realisees": [
                    "Recettage de 12 nouveaux scripts Stambia sur l''environnement de qualification",
                    "Optimisation des temps d''exécution des tables volumineuses de NODHOS (gain moyen de 28%)",
                    "Mise à jour des fiches consignes d''exploitation pour l''équipe d''astreinte"
                ],
                "decisions": [
                    "Suppression définitive des anciens scripts PL/SQL dépréciés dès validation du RUN",
                    "Planification de la formation Stambia Avancé pour l''équipe support au mois d''octobre"
                ]
            }
        ]
    }'::jsonb
)
ON CONFLICT (report_date) DO UPDATE
SET raw_summary = EXCLUDED.raw_summary,
    updated_at = timezone('utc'::text, now());
