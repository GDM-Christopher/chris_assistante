#!/usr/bin/env python3
"""Assistant de configuration interactive pour l'authentification Google Workspace.

Ce script permet de générer localement le fichier `token.json` grâce au flux OAuth2,
puis affiche la commande PowerShell pour l'encoder en Base64 pour vos Secrets GitHub.

Usage :
    1. Téléchargez votre fichier 'client_secret_xxx.json' depuis Google Cloud Console.
    2. Renommez-le 'credentials.json' à la racine de ce dossier.
    3. Exécutez : python setup_google_auth.py
"""

import base64
import json
import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
]


def main():
    print("=" * 70)
    print("CONFIGURATION DE L'AUTHENTIFICATION GOOGLE WORKSPACE")
    print("=" * 70)

    creds_file = Path("credentials.json")
    if not creds_file.exists():
        # Recherche d'un fichier client_secret*.json téléchargé par défaut depuis Google Cloud
        candidates = list(Path(".").glob("client_secret*.json"))
        if candidates:
            creds_file = candidates[0]
            print(f"\nℹ️ Fichier détecté automatiquement : {creds_file.name}")
        else:
            print("\n❌ Fichier 'credentials.json' introuvable dans le dossier actuel.")
            print("Étapes à suivre :")
            print("1. Rendez-vous sur Google Cloud Console : https://console.cloud.google.com/")
            print("2. Créez des identifiants 'ID client OAuth' (Type : Application de bureau).")
            print("3. Téléchargez le JSON et enregistrez-le sous le nom 'credentials.json' ici.")
            print("4. Relancez ensuite ce script : .\\.venv\\Scripts\\python setup_google_auth.py\n")
            sys.exit(1)

    print("\nLancement du serveur d'autorisation local...")
    print("Votre navigateur va s'ouvrir pour vous permettre d'autoriser l'application.\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
        creds = flow.run_local_server(port=0)

        token_file = Path("token.json")
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        print(f"\n✅ Jeton d'accès sauvegardé avec succès dans : {token_file.resolve()}")

        # Génération du token en Base64 pour GitHub Secrets
        with open(token_file, "rb") as f:
            b64_token = base64.b64encode(f.read()).decode("utf-8")

        print("\n" + "=" * 70)
        print("SECRET GITHUB ACTIONS (GOOGLE_CREDENTIALS_BASE64) :")
        print("=" * 70)
        print("Pour automatiser l'ingestion dans GitHub Actions, ajoutez ce secret :")
        print(f"\nNom du secret : GOOGLE_CREDENTIALS_BASE64\n")
        print(f"Valeur à copier-coller :\n{b64_token}\n")
        print("=" * 70)
        print("🎉 Authentification locale et Cloud configurée avec succès !")

    except Exception as e:
        print(f"\n❌ Erreur lors du flux d'authentification : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
