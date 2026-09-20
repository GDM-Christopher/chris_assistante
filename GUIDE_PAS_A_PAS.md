# 📘 Guide Pas-à-Pas : Déploiement & Exploitation de la Solution de Supervision Technique

Ce guide exhaustif vous accompagne pas à pas pour configurer, exécuter en local, automatiser via GitHub Actions et déployer sur Render votre tableau de bord de supervision technique.

---

## 📑 Sommaire
1. [Étape 1 : Configuration de la Base de Données Supabase](#étape-1--configuration-de-la-base-de-données-supabase)
2. [Étape 2 : Configuration des Identifiants Google Workspace](#étape-2--configuration-des-identifiants-google-workspace)
3. [Étape 3 : Obtention de la Clé API Gemini 1.5 Pro](#étape-3--obtention-de-la-clé-api-gemini-15-pro)
4. [Étape 4 : Test et Exécution en Local sur votre PC](#étape-4--test-et-exécution-en-local-sur-votre-pc)
5. [Étape 5 : Initialisation Git & Secrets GitHub Actions](#étape-5--initialisation-git--secrets-github-actions)
6. [Étape 6 : Déploiement Web sur Render](#étape-6--déploiement-web-sur-render)

---

## Étape 1 : Configuration & Déploiement Automatique de la BDD Supabase

Pour une infrastructure professionnelle ("GitOps"), la base de données est désormais **entièrement synchronisée avec GitHub**. Dès que vous ajoutez ou modifiez un fichier dans le dossier `supabase/migrations/` et que vous poussez sur `main`, GitHub Actions exécute automatiquement les migrations sur Supabase !

### 1.1 Créer votre projet Supabase
1. Rendez-vous sur [Supabase](https://supabase.com/) et connectez-vous.
2. Cliquez sur **"New Project"**.
3. Renseignez un nom (ex: `chris-supervision`) et définissez un **mot de passe fort pour la base de données** (notez-le bien, il sert pour `SUPABASE_DB_PASSWORD`).
4. Choisissez la région la plus proche (ex: `Frankfurt (eu-central-1)`).

### 1.2 Récupérer vos Identifiants Supabase pour GitHub
Pour que GitHub puisse déployer les tables automatiquement sur Supabase, vous avez besoin de 3 informations :
1. **Référence du Projet (`SUPABASE_PROJECT_REF`)** :
   - Visible dans l'URL de votre projet : `https://supabase.com/dashboard/project/<VOTRE_PROJECT_REF>`
   - Ou dans **Project Settings** > **General** > **Reference ID**.
2. **Mot de passe de la Base de Données (`SUPABASE_DB_PASSWORD`)** :
   - Le mot de passe que vous avez défini à la création du projet.
   - *(En cas d'oubli, vous pouvez le réinitialiser dans Project Settings > Database > Reset Database Password)*.
3. **Jeton d'Accès Personnel Supabase (`SUPABASE_ACCESS_TOKEN`)** :
   - Cliquez sur votre avatar en bas à gauche > **Account Settings** (ou rendez-vous sur [https://supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens)).
   - Cliquez sur **"Generate new token"**, nommez-le `github-actions-deploy`, et copiez la clé générée.

### 1.3 Comment fonctionne le Déploiement Automatique ?
- Vos migrations SQL sont stockées dans `supabase/migrations/` (ex: `20260920144000_create_daily_reports.sql`).
- Le workflow GitHub Actions `.github/workflows/supabase_deploy.yml` est pré-configuré dans le projet.
- Dès que vous faites un `git push` contenant une nouvelle migration ou une modification, **GitHub Actions se connecte à Supabase et applique les changements automatiquement** (`supabase db push`). Plus besoin de faire de copier-coller manuel !

### 1.4 Récupérer les clés d'accès API pour l'Application
1. Allez dans **Project Settings** > **API**.
2. Notez deux valeurs indispensables pour l'application Streamlit et le runner d'ingestion :
   - **Project URL** (ex: `https://xyzcompany.supabase.co`) -> `SUPABASE_URL`.
   - **Project API Keys** :
     * `anon` / `public` -> clé publique pour l'application Streamlit.
     * `service_role` -> clé secrète avec droits d'écriture complets pour `SUPABASE_KEY` dans le runner et Render.

*(Note de secours : Si vous préférez exécuter le SQL manuellement au début, le script complet est également disponible dans `supabase_schema.sql` et peut être exécuté dans le SQL Editor de Supabase).*


## Étape 2 : Configuration des Identifiants Google Workspace

Le projet se connecte à l'API **Gmail** (en mode aspiration intégrale sur 48h sans filtre de mot-clé restrictif, l'IA Gemini effectuant elle-même le tri intelligent pour ne rien manquer : incidents OneStock, Stambia, OPCON, projets Snowflake, WinWig, réassort...) et à l'API **Google Chat**.

Deux méthodes sont disponibles :
- **Méthode A (Recommandée pour débuter) : ID Client OAuth 2.0 Bureau**
- **Méthode B (Avancée) : Compte de Service avec Délégation de Domaine**

### Méthode A : OAuth 2.0 (Recommandée)
1. Ouvrez la [Google Cloud Console](https://console.cloud.google.com/).
2. Créez un projet ou sélectionnez votre projet existant.
3. Activez les APIs nécessaires :
   - Allez dans **APIs & Services** > **Bibliothèque (Library)**.
   - Recherchez et activez **Gmail API**.
   - Recherchez et activez **Google Chat API**.
4. Configurez l'écran de consentement OAuth :
   - Allez dans **APIs & Services** > **OAuth consent screen**.
   - Type : **Interne** (si Google Workspace d'entreprise) ou **Externe**.
   - Ajoutez les scopes suivants :
     * `https://www.googleapis.com/auth/gmail.readonly`
     * `https://www.googleapis.com/auth/chat.messages.readonly`
     * `https://www.googleapis.com/auth/chat.spaces.readonly`
   - Si externe, ajoutez votre adresse e-mail dans la liste des utilisateurs tests ("Test users").
5. Créez les identifiants :
   - Allez dans **Identifiants (Credentials)** > **Créer des identifiants** > **ID client OAuth**.
   - Type d'application : **Application de bureau (Desktop app)**.
   - Cliquez sur **Créer**, puis **Télécharger le fichier JSON**.
6. Enregistrez ce fichier sous le nom `credentials.json` à la racine de votre projet local `chris_assistante/`.
7. Lancez le script interactif fourni dans ce projet :
   ```powershell
   python setup_google_auth.py
   ```
8. Une page de navigateur s'ouvre : connectez-vous avec votre compte Google et acceptez les autorisations.
9. Le script crée automatiquement le fichier `token.json` et affiche sa version encodée en Base64 prête pour GitHub Actions !

---

## Étape 3 : Obtention de la Clé API Gemini 1.5 Pro

1. Rendez-vous sur [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Connectez-vous avec votre compte Google.
3. Cliquez sur **"Create API Key"**.
4. Copiez la clé générée (commençant par `AIzaSy...`).
5. Cette clé correspond à `GEMINI_API_KEY`.

---

## Étape 4 : Test et Exécution en Local sur votre PC

### 4.1 Préparer le fichier `.env`
À la racine de `chris_assistante/`, créez une copie de `.env.example` nommée `.env` :
```powershell
Copy-Item .env.example .env
```
Éditez `.env` avec vos vraies valeurs :
```ini
GEMINI_API_KEY="AIzaSy..."
SUPABASE_URL="https://votre-projet.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUz..."
```

### 4.2 Installer les dépendances Python
Dans votre terminal PowerShell :
```powershell
# Création d'un environnement virtuel (recommandé)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installation des paquets requis
pip install -r requirements.txt
```

### 4.3 Tester le Runner Backend

**Option 1 : Test instantané avec données simulées (sans appeler les APIs Google)**
```powershell
python backend/daily_runner.py --mock --dry-run
```
*Le script simule des e-mails d'incidents OneStock, OPCON et Stambia, interroge Gemini 1.5 Pro et affiche le JSON produit sans toucher à Supabase.*

**Option 2 : Injection des données de test dans Supabase**
```powershell
python backend/daily_runner.py --sample-upload
```
*Le script injecte immédiatement le rapport dans votre table `daily_reports` de Supabase.*

**Option 3 : Exécution complète réelle (Google Workspace -> Gemini -> Supabase)**
```powershell
python backend/daily_runner.py
```

### 4.4 Lancer le Dashboard Streamlit
```powershell
streamlit run app.py
```
Streamlit s'ouvrira automatiquement sur `http://localhost:8501`.
Vous aurez accès :
- Aux cartes KPI (Santé globale, incidents, alertes).
- Aux alertes majeures du jour.
- Au registre des incidents avec filtres par statut, base de données et flux.
- Aux fiches projets avec accordéons dépliables et décisions.

---

## Étape 5 : Initialisation Git & Secrets GitHub Actions

### 5.1 Vérification de l'état Git et Push
Le dépôt est configuré pour pointer vers votre remote GitHub : `https://github.com/GDM-Christopher/chris_assistante.git`.

Pour envoyer vos commits vers GitHub :
```powershell
git add .
git commit -m "feat: initial commit - supervision dashboard Streamlit, Gemini & Supabase"
git push -u origin main
```

### 5.2 Déclarer les Secrets sur GitHub
Pour activer à la fois l'**ingestion quotidienne automatique** et le **déploiement automatique de la BDD Supabase** :
1. Sur GitHub, accédez à votre dépôt : `https://github.com/GDM-Christopher/chris_assistante`.
2. Allez dans **Settings** > **Secrets and variables** > **Actions**.
3. Cliquez sur **"New repository secret"** et ajoutez les variables suivantes :

#### A. Secrets pour l'Analyse & l'Ingestion Quotidienne (Cron 08:00 UTC)
| Nom du Secret | Description / Valeur |
| :--- | :--- |
| `GEMINI_API_KEY` | Votre clé Google AI Studio (`AIzaSy...`) |
| `SUPABASE_URL` | L'URL de votre projet Supabase (`https://xxx.supabase.co`) |
| `SUPABASE_KEY` | La clé `service_role` de Supabase (pour autoriser l'écriture) |
| `GOOGLE_CREDENTIALS_BASE64` | Le contenu Base64 de votre `token.json` ou `service_account.json` |

#### B. Secrets pour le Déploiement Automatique BDD Supabase (Migrations)
| Nom du Secret | Description / Valeur |
| :--- | :--- |
| `SUPABASE_PROJECT_REF` | Référence du projet Supabase (ex: `abcdefghijklmnopqrst`) |
| `SUPABASE_DB_PASSWORD` | Mot de passe de votre base PostgreSQL Supabase |
| `SUPABASE_ACCESS_TOKEN` | Jeton d'accès personnel généré sur https://supabase.com/dashboard/account/tokens |

> 💡 **Astuce pour obtenir la valeur Base64 en PowerShell :**
> ```powershell
> [Convert]::ToBase64String([IO.File]::ReadAllBytes("token.json")) | Set-Clipboard
> ```
> Le contenu est directement copié dans votre presse-papier !

### 5.3 Tester manuellement le Workflow GitHub Actions
1. Dans GitHub, allez dans l'onglet **Actions**.
2. Sélectionnez le workflow **"Ingestion & Analyse Quotidienne (Cron 08:00 UTC)"**.
3. Cliquez sur **"Run workflow"** > **Run workflow**.
4. Suivez l'exécution des logs en temps réel.

---

## Étape 6 : Déploiement Web sur Render

L'application Streamlit peut être hébergée gratuitement et en continu sur [Render](https://render.com/).

### 6.1 Créer le Web Service sur Render
1. Connectez-vous sur votre tableau de bord [Render](https://dashboard.render.com/).
2. Cliquez sur **"New +"** > **"Web Service"**.
3. Connectez votre compte GitHub et sélectionnez le dépôt **`GDM-Christopher/chris_assistante`**.
4. Renseignez les paramètres de déploiement :
   - **Name** : `chris-supervision-dashboard`
   - **Region** : `Frankfurt (EU Central)`
   - **Branch** : `main`
   - **Runtime** : `Python 3`
   - **Build Command** :
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command** :
     ```bash
     streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
     ```
   - **Plan** : `Free`

### 6.2 Déclarer les Variables d'Environnement sur Render
Dans la section **"Environment Variables"** de votre Web Service Render, ajoutez :
- `PYTHON_VERSION` = `3.11.9`
- `SUPABASE_URL` = *(votre URL Supabase)*
- `SUPABASE_KEY` = *(votre clé anon ou service_role)*
- `GEMINI_API_KEY` = *(votre clé Gemini)*

### 6.3 Déployer !
Cliquez sur **"Create Web Service"**.
Render compile l'application et vous fournit une URL publique sécurisée HTTPS (ex: `https://chris-supervision-dashboard.onrender.com`).
Votre dashboard est désormais accessible 24/7 depuis n'importe quel navigateur !
