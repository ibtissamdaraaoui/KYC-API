import os
import base64
import requests # Assurez-vous que 'requests' est dans votre requirements.txt

# --- Configuration de la connexion à Vault ---
# Récupérés depuis les variables d'environnement chargées au démarrage du service.
VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")
import logging

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
    if vault_path.startswith("secret/keys/"):
        api_path = vault_path.replace("secret/keys/", "secret/data/keys/")
    else:
        api_path = f"secret/data/{vault_path.lstrip('/')}"
    
    # --- Construction de la requête HTTP ---
    url = f"{VAULT_ADDR}/v1/{api_path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    
    logging.info(f"   - Appel à l'API Vault : GET {url}")

    try:
        # --- Exécution de l'appel à l'API ---
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        # --- Analyse de la réponse JSON ---
        secret_container = response.json().get("data", {}).get("data", {})
        encoded_key = secret_container.get("aes_key") or secret_container.get("key")

        if not encoded_key:
            raise KeyError(f"La clé 'aes_key' ou 'key' est introuvable dans la réponse de Vault pour le chemin '{vault_path}'.")

        # --- Décodage et retour de la clé ---
        return base64.b64decode(encoded_key)

    except requests.exceptions.HTTPError as e:
        raise Exception(f"Erreur HTTP de Vault ({e.response.status_code}) pour le chemin '{vault_path}': {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erreur de communication avec Vault à l'adresse {VAULT_ADDR}: {e}")
    except (KeyError, TypeError) as e:
        # json.JSONDecodeError est déjà géré par response.json() ou response.raise_for_status()
        raise Exception(f"Erreur lors de l'analyse de la réponse de Vault. Structure inattendue. Erreur: {e}")