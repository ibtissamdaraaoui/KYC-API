# Fichier: workflow_service/app/kong_client.py
import os
import requests

KONG_ADMIN_URL = os.getenv("KONG_ADMIN_URL")
if not KONG_ADMIN_URL:
    raise ValueError("KONG_ADMIN_URL n'est pas défini dans le .env central")

def provision_client_on_kong(application_id: str) -> str:
    """
    Provisionne un client sur Kong (crée un Consumer et une JWT Credential)
    et retourne le secret JWT unique généré par Kong.
    """
    print(f"--- Provisionnement KONG pour '{application_id}' ---")
    try:
        # Étape 1: Créer le Consumer
        consumers_url = f"{KONG_ADMIN_URL}/consumers"
        consumer_payload = {"username": application_id}
        response = requests.post(consumers_url, json=consumer_payload)
        if response.status_code not in [201, 409]: # 201=Créé, 409=Existe déjà (idempotent)
            response.raise_for_status()
        print(f"-> Consumer '{application_id}' OK.")

        # Étape 2: Créer la JWT Credential. Kong génère le secret pour nous.
        jwt_url = f"{KONG_ADMIN_URL}/consumers/{application_id}/jwt"
        response = requests.post(jwt_url, json={"key": application_id, "algorithm": "HS256"})

        if response.status_code == 201: # Si la credential vient d'être créée
            print(f"-> Nouvelle JWT Credential pour '{application_id}' créée.")
            secret = response.json().get('secret')
        elif response.status_code == 409: # Si elle existait déjà, on la récupère
            print(f"-> JWT Credential pour '{application_id}' existe déjà. Récupération...")
            get_response = requests.get(jwt_url)
            get_response.raise_for_status()
            # La réponse est une liste, on prend la première credential
            secret = get_response.json()['data'][0]['secret']
        else: # Gérer les autres erreurs HTTP
            response.raise_for_status()

        if not secret:
            raise Exception("N'a pas pu créer ou récupérer le secret JWT depuis Kong.")

        print(f"--- Provisionnement KONG pour '{application_id}' terminé. ---")
        return secret

    except requests.exceptions.RequestException as e:
        print(f"❌ ERREUR KONG: Impossible de contacter l'API Admin de Kong. {e}")
        raise