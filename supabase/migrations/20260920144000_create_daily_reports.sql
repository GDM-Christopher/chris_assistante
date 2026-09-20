-- ==============================================================================
-- MIGRATION SUPABASE : 20260920144000_create_daily_reports.sql
-- Description : Création de la table daily_reports, index, trigger et RLS
-- Déployé automatiquement via GitHub Actions sur git push
-- ==============================================================================

-- 1. Activation de l'extension pgcrypto
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
CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON public.daily_reports (report_date DESC);
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

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'daily_reports' AND policyname = 'Permettre la lecture des rapports pour tous'
    ) THEN
        CREATE POLICY "Permettre la lecture des rapports pour tous"
            ON public.daily_reports
            FOR SELECT
            USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'daily_reports' AND policyname = 'Permettre l insertion/mise a jour pour la cle service'
    ) THEN
        CREATE POLICY "Permettre l insertion/mise a jour pour la cle service"
            ON public.daily_reports
            FOR ALL
            USING (auth.role() = 'service_role' OR auth.role() = 'anon')
            WITH CHECK (auth.role() = 'service_role' OR auth.role() = 'anon');
    END IF;
END $$;
