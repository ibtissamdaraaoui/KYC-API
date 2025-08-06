# Fichier: matching_service/app/vault_client.py

import os
import base64
import requests # Assurez-vous que 'requests' est dans votre requirements.txt
from dotenv import load_dotenv
import json 

# Charger les variables d'environnement depuis un fichier .env
load_dotenv()

# --- Configuration de la connexion à Vault ---
# Récupérés depuis les variables d'environnement.
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN","root")

# Vérification critique au démarrage du service
if not VAULT_ADDR or not VAULT_TOKEN:
    raise ValueError("Les variables d'environnement VAULT_ADDR ou VAULT_TOKEN sont manquantes.")

# --- Fonction principale pour récupérer une clé ---
def load_key_from_vault(vault_path: str) -> bytes:
    """
    Récupère une clé AES depuis Vault en utilisant son chemin.
    Ce code est basé sur celui du verification_service, avec une gestion
    d'erreurs améliorée pour plus de robustesse.

    Args:
        vault_path (str): Le chemin du secret (ex: 'secret/keys/mon-cas-kyc').

    Returns:
        bytes: La clé de déchiffrement décodée.
    """
    if not vault_path:
        raise ValueError("Le chemin de la clé Vault ne peut pas être vide.")

    # --- Préparation du chemin pour l'API KV v2 ---
    # Votre logique existante pour insérer '/data/' est conservée.
    if vault_path.startswith("secret/keys/"):
        api_path = vault_path.replace("secret/keys/", "secret/data/keys/")
    else:
        # Cas générique pour d'autres chemins possibles
        api_path = f"secret/data/{vault_path.lstrip('/')}"
    
    # --- Construction de la requête HTTP ---
    url = f"{VAULT_ADDR}/v1/{api_path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    
    print(f"   - Appel à l'API Vault : GET {url}")

    try:
        # --- Exécution de l'appel à l'API ---
        response = requests.get(url, headers=headers, timeout=5) # Ajout d'un timeout

        # Lève une exception (HTTPError) si le statut est 4xx ou 5xx.
        # C'est plus propre que de vérifier le status_code manuellement.
        response.raise_for_status()

        # --- Analyse de la réponse JSON ---
        # Le secret est niché dans response.json()['data']['data']
        secret_container = response.json().get("data", {}).get("data", {})
        
        # On récupère la clé encodée en Base64.
        encoded_key = secret_container.get("aes_key") or secret_container.get("key")

        if not encoded_key:
            raise KeyError(f"La clé 'aes_key' est introuvable dans la réponse de Vault pour le chemin '{vault_path}'.")

        # --- Décodage et retour de la clé ---
        return base64.b64decode(encoded_key)

    except requests.exceptions.HTTPError as e:
        # Gère spécifiquement les erreurs HTTP (404 Not Found, 403 Forbidden, 500 Server Error...)
        raise Exception(f"Erreur HTTP de Vault ({e.response.status_code}) pour le chemin '{vault_path}': {e.response.text}")
    except requests.exceptions.RequestException as e:
        # Gère les erreurs réseau (connexion refusée, timeout...)
        raise Exception(f"Erreur de communication avec Vault à l'adresse {VAULT_ADDR}: {e}")
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        # Gère les cas où la réponse de Vault n'a pas la structure attendue.
        raise Exception(f"Erreur lors de l'analyse de la réponse de Vault. Structure inattendue. Erreur: {e}")