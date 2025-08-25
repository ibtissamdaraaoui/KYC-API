import os
import base64
import requests


VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

# --- AJOUT DE LA VÉRIFICATION CRITIQUE ---
if not VAULT_ADDR or not VAULT_TOKEN:
    raise ValueError("Les variables d'environnement VAULT_ADDR ou VAULT_TOKEN sont manquantes.")

def load_key_from_vault(vault_path: str) -> bytes:
    """
    vault_path vient de la base ➜ "secret/keys/..."
    On doit le convertir en URL KV v2 ➜ "secret/data/keys/..."
    """
    if vault_path.startswith("secret/keys/"):
        api_path = vault_path.replace("secret/keys/", "secret/data/keys/")
    else:
        # si tu montes d’autres paths plus tard
        api_path = f"secret/data/{vault_path.lstrip('/')}"
    
    url = f"{VAULT_ADDR}/v1/{api_path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Vault error (GET): {r.status_code} - {r.text}")

    encoded_key = r.json()["data"]["data"]["aes_key"]
    return base64.b64decode(encoded_key)
