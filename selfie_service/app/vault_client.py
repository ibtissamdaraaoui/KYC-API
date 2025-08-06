# Fichier: selfie_service/app/vault_client.py

import hvac
import os
import base64  # <--- IMPORTER BASE64

from dotenv import load_dotenv
from pathlib import Path

# Force le chemin : projet racine
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")

client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

def store_key_in_vault(key_id: str, key_bytes: bytes) -> str:
    """
    Stocke la clé dans Vault après l'avoir encodée en Base64.
    """
    path = f'selfie-keys/{key_id}'
    
    # --- CORRECTION ---
    # 1. Encoder les bytes bruts en une chaîne de caractères Base64
    encoded_key_str = base64.b64encode(key_bytes).decode('utf-8')

    # 2. Stocker la chaîne encodée
    client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={"key": encoded_key_str}  # On stocke la chaîne, pas les bytes .hex()
    )
    return path   

def get_key_from_vault(key_id: str) -> bytes:
    """
    Récupère la clé depuis Vault et la décode de Base64 vers des bytes.
    """
    path = f'selfie-keys/{key_id}'
    read_response = client.secrets.kv.v2.read_secret_version(path=path)
    
    # --- CORRECTION ---
    # Récupérer la chaîne encodée et la décoder en bytes
    encoded_key_str = read_response['data']['data']['key']
    return base64.b64decode(encoded_key_str)