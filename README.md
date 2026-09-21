# ⚡ Supervision Technique SI & Tableau de Bord Intelligent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Gemini 2.5 Flash](https://img.shields.io/badge/IA-Gemini%202.5%20Flash-4285F4.svg)](https://aistudio.google.com/)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20Postgres-3ECF8E.svg)](https://supabase.com/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-Daily%20Cron-2088FF.svg)](https://github.com/features/actions)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7.svg)](https://render.com/)

Plateforme complète de supervision technique quotidienne ingérant l'intégralité des flux de communication de production (e-mails Gmail DSI/OPCON/Stambia/OneStock/Supply/Snowflake, salons Google Chat et invitations Google Calendar), analysée et filtrée automatiquement par **Gemini 2.5 Flash**, stockée dans **Supabase**, et visualisée via un tableau de bord **Streamlit** moderne et réactif.

---

## 🏗️ Architecture Globale

```text
[Gmail API] (Aspiration intégrale 48h sans filtre de mot-clé) ──┐
[Google Chat API] (Messages & Salons récents)                ──┼──> [backend/daily_runner.py]
[Google Calendar / Invitations Gmail] (Agendas à venir)       ──┘            │
                                                                             ▼
                                                                    [Gemini 2.5 Flash]
                                                            (Tri autonome du bruit & Extraction)
                                                                             │
                                                                             ▼
                                                                    [Supabase Database]
                                                                  (Table: daily_reports)
                                                                             │
                                                                             ▼
                                                                   [Streamlit Dashboard]
                                                    (5 Onglets : KPIs, Incidents, Projets, Réunions, Copilote)
```

---

## 🚀 Fonctionnalités Clés

- 📥 **Aspiration Globale & Tri Cognitif Intelligent (Zero Mot-Clé Manuel)** :
  - Ingestion de **100% des e-mails récents sur 48 heures** (couvrant tout le week-end) sans aucun filtre restrictif.
  - **Filtre cognitif par Gemini 2.5 Flash** : L'IA élimine d'elle-même le bruit (newsletters, spams, invitations automatiques, RH généraux) et capture le signal métier et technique (OneStock, Stambia, OPCON, Snowflake, WinWig, ERP, réassorts...).
- 🔗 **Traçabilité & Liens Directs vers les Sources** :
  - Chaque incident, alerte et projet dispose d'un bouton cliquable ouvrant directement le fil de discussion dans **Gmail** (`https://mail.google.com/mail/u/0/#all/{thread_id}`) ou le salon dans **Google Chat**.
- 📅 **Module Réunions à Venir & Préparations Intelligentes** :
  - Détection automatique des réunions à venir (invitations d'agenda et courriels de cadrage).
  - Identification des thématiques et de l'ordre du jour.
  - Élaboration automatique de la **checklist de préparation sur-mesure pour Christopher** en croisant le sujet avec les e-mails et messages récents.
  - **Simulateur de réunion IA interactif** pour poser des questions spécifiques (pitch d'intro de 1 min, questions pièges...).
- 🧠 **Copilote DSI & Décryptage Pédagogique** :
  - **Photo Globale du SI** : Génération d'une synthèse non-jargonnée prête pour le Comité de Direction.
  - **Vulgarisateur Technique** : Explication simple et accessible de n'importe quel concept, flux ou base de données.
  - **Assistant conversationnel** intégré.
- 🗄️ **Persistance Idempotente Supabase & Cache Local** :
  - Table PostgreSQL `daily_reports` avec index GIN JSONB et RLS.
  - Cache local instantané (`backend/latest_report.json`) garantissant un affichage immédiat même hors-ligne.
- ⏰ **Automatisation Quotidienne (Cron)** :
  - Workflow GitHub Actions exécuté chaque matin à 08:00 UTC.
- 🌐 **Hébergement Cloud Render** :
  - Déploiement en continu via Web Service Render (100% gratuit).

---

## 📁 Arborescence du Projet

```text
chris_assistante/
├── backend/
│   ├── config.py                     # Paramètres centralisés (ingestion globale 48h, modèles)
│   ├── google_auth.py                # Authentification Google Workspace (OAuth2 & Service Account)
│   ├── gmail_client.py               # Ingestion intégrale Gmail (avec génération d'URLs web)
│   ├── chat_client.py                # Ingestion des salons et messages Google Chat
│   ├── meetings_client.py            # Ingestion des invitations et réunions à venir
│   ├── gemini_analyzer.py            # Moteur IA (Gemini 2.5 Flash, schémas Pydantic stricts)
│   ├── supabase_client.py            # Client d'accès et persistance PostgreSQL Supabase
│   ├── mock_data.py                  # Jeu de données de simulation DSI pour tests hors-ligne
│   ├── daily_runner.py               # Orchestrateur central CLI (production, mock, dry-run)
│   └── latest_report.json            # Cache local du dernier rapport généré
├── app.py                            # Interface frontend Streamlit (5 onglets interactifs)
├── supabase_schema.sql               # Schéma SQL PostgreSQL complet (tables, index, RLS)
├── setup_google_auth.py              # Assistant interactif de connexion Google OAuth en local
├── requirements.txt                  # Dépendances Python
├── render.yaml                       # Blueprint de déploiement Cloud sur Render
├── .env.example                      # Modèle des variables d'environnement
├── .gitignore                        # Protection des secrets et données sensibles
├── GUIDE_PAS_A_PAS.md                # Guide complet de configuration et mise en production
├── SYNTHESE_GLOBALE_ARCHITECTURE.md  # Dossier d'architecture et de conception technique
└── README.md                         # Présentation générale du projet
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

### 2. Lancer le Tableau de Bord Streamlit
```powershell
streamlit run app.py
```
L'application s'ouvre sur `http://localhost:8501` avec ses **5 onglets opérationnels** :
1. **📊 Vue d'ensemble & Alertes** : Santé globale, KPI cards, synthèse exécutive.
2. **🚨 Incidents & Résolutions Techniques** : Registre filtrable avec liens directs Gmail/Chat.
3. **🚀 Avancement par Projet** : Suivi des chantiers (Snowflake, Stambia, Logys...) et arbitrages.
4. **📅 Réunions à Venir & Préparations** : Ordre du jour, checklist de préparation IA et simulateur.
5. **🧠 Copilote DSI & Décryptage Tech** : Photo CODIR, vulgarisateur et assistant interactif.

### 3. Lancer une Ingestion Réelle
```powershell
# Ingestion des dernières 72h (couvre le week-end, boîte complète, Google Chat et réunions)
python backend/daily_runner.py --hours 72
```
*Le runner récupère les échanges des salons Google Chat ciblés (dont `La DOSI - Equipe Data / IA`, `La DOSI - Espace PRO`, groupes support), les e-mails récents et les réunions de la semaine, puis extrait une synthèse consolidée avec liens directs vers chaque source.*

---

## 📖 Documentation Complète

Pour configurer Supabase, vos identifiants Google Workspace, vos secrets GitHub Actions et déployer sur Render :
👉 **[Consulter le GUIDE_PAS_A_PAS.md](file:///c:/Users/cgilleron/chris_assistante/GUIDE_PAS_A_PAS.md)**  
👉 **[Consulter la SYNTHESE_GLOBALE_ARCHITECTURE.md](file:///c:/Users/cgilleron/chris_assistante/SYNTHESE_GLOBALE_ARCHITECTURE.md)**
