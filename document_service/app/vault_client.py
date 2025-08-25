# app/vault_client.py

import os
import base64
import requests
from datetime import datetime

VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

def store_key_in_vault(aes_key: bytes, kyc_case_id: str) -> str:
    """
    Stocke une clé AES-256 dans Vault sous un chemin unique.
    Retourne le chemin Vault à stocker dans la base.
    """
    path = f"secret/data/keys/{kyc_case_id}_{datetime.utcnow().timestamp()}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    payload = {
        "data": {
            "aes_key": base64.b64encode(aes_key).decode()
        }
    }

    response = requests.post(f"{VAULT_ADDR}/v1/{path}", headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Vault error: {response.status_code} - {response.text}")

    return path.replace("data/", "")  # retourne `secret/keys/...`
