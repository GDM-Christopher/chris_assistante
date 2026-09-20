# ⚡ Supervision Technique SI & Tableau de Bord Intelligent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Gemini 1.5 Pro](https://img.shields.io/badge/IA-Gemini%201.5%20Pro-4285F4.svg)](https://aistudio.google.com/)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20Postgres-3ECF8E.svg)](https://supabase.com/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-Daily%20Cron-2088FF.svg)](https://github.com/features/actions)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7.svg)](https://render.com/)

Plateforme complète de supervision technique quotidienne ingérant les communications de production (e-mails Gmail DSI/OPCON/Stambia/OneStock et Google Chat), synthétisée automatiquement par **Gemini 1.5 Pro**, stockée dans **Supabase**, et visualisée via un tableau de bord **Streamlit** moderne et réactif.

---

## 🏗️ Architecture Globale

```text
[Gmail API] (OneStock, DSI, OPCON, Stambia)  ──┐
                                               ├──> [backend/daily_runner.py]
[Google Chat API] (Espaces & Messages 24h)   ──┘            │
                                                            ▼
                                                   [Gemini 1.5 Pro]
                                           (Extraction JSON ultra-structurée)
                                                            │
                                                            ▼
                                                   [Supabase Database]
                                                 (Table: daily_reports)
                                                            │
                                                            ▼
                                                  [Streamlit Dashboard]
                                            (KPIs, Alertes, Incidents, Projets)
```

---

## 🚀 Fonctionnalités Clés

- 📥 **Ingestion Multi-Sources 24h** : Filtre intelligent des e-mails Gmail selon vos libellés clés (`OneStock via RUN`, `Notification_DSI`, `OPCON`, `trt_stambia`, etc.) et collecte des échanges Google Chat d'astreinte.
- 🤖 **Analyse IA par Gemini 1.5 Pro** : Extraction garantie conforme à un schéma strict Pydantic (Santé globale, Alertes critiques, Incidents avec causes racines & solutions, Avancement par projet).
- 🗄️ **Persistance Idempotente Supabase** : Table PostgreSQL `daily_reports` avec index GIN JSONB et sécurité RLS.
- 📊 **Interface Streamlit Interactive (`app.py`)** :
  - **Vue d'ensemble** : Statut global SI (Vert/Orange/Rouge), compteurs d'incidents résolus/en cours, métriques, alertes majeures.
  - **Incidents & Résolutions** : Moteur de recherche plein texte, filtres croisés dynamiques (par statut, base de données, flux impacté), fiches détaillées avec blocs de code technique et export CSV.
  - **Avancement par Projet** : Accordéons organisés par projet, synthétisant les actions achevées et les décisions prises.
- ⏰ **Automatisation Quotidienne (Cron)** : Workflow GitHub Actions (`.github/workflows/daily_cron.yml`) exécuté tous les matins à 08:00 UTC.
- 🌐 **Déploiement Cloud Render** : Fichier Blueprint `render.yaml` prêt à l'emploi.

---

## 📁 Arborescence du Projet

```text
chris_assistante/
├── .github/workflows/daily_cron.yml  # Automatisation quotidienne GitHub Actions
├── backend/
│   ├── config.py                     # Gestion des variables d'environnement
│   ├── google_auth.py                # Authentification Google (OAuth2 & Service Account)
│   ├── gmail_client.py               # Extraction et nettoyage des e-mails Gmail
│   ├── chat_client.py                # Récupération des messages Google Chat
│   ├── gemini_analyzer.py            # Prompt strict et inférence Gemini 1.5 Pro
│   ├── supabase_client.py            # Client de persistance Supabase
│   ├── mock_data.py                  # Messages de test et simulation réaliste DSI
│   └── daily_runner.py               # Orchestrateur CLI (modes réel, mock, dry-run)
├── app.py                            # Application frontend Streamlit
├── supabase_schema.sql               # Schéma SQL PostgreSQL (table, index, RLS, seed)
├── setup_google_auth.py              # Assistant de connexion Google OAuth en local
├── requirements.txt                  # Dépendances Python
├── render.yaml                       # Blueprint de déploiement Render
├── .env.example                      # Gabarit des secrets et variables d'environnement
├── .gitignore                        # Protection des clés privées et tokens
├── GUIDE_PAS_A_PAS.md                # Documentation complète de mise en production
└── README.md                         # Présentation du projet
```

---

## ⚡ Démarrage Rapide

### 1. Installation en Local
```powershell
# Cloner le dépôt et se placer dans le dossier
git clone https://github.com/GDM-Christopher/chris_assistante.git
cd chris_assistante

# Créer un environnement virtuel
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Tester immédiatement le Dashboard
```powershell
# Lancer Streamlit (affichera des données d'exemple si Supabase n'est pas encore relié)
streamlit run app.py
```

### 3. Tester le Runner IA en Simulation
```powershell
# Déclenche l'analyse Gemini sur un jeu de messages de test (nécessite juste GEMINI_API_KEY dans .env)
python backend/daily_runner.py --mock --dry-run
```

---

## 📖 Guide de Configuration Détaillé

Pour configurer Supabase, vos identifiants Google Workspace, vos secrets GitHub Actions et déployer sur Render, consultez le guide pas-à-pas complet :
👉 **[Consulter GUIDE_PAS_A_PAS.md](file:///C:/Users/cgilleron/chris_assistante/GUIDE_PAS_A_PAS.md)**
