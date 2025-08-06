import base64
from typing import Tuple
from app.minio_client import s3_client, MINIO_BUCKET
from app.database import SessionLocal
from app.models import Document
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from app.vault_client import load_key_from_vault


# ────────────────────────────────────────────────────────────────
# Déchiffrement AES-256 (même algorithme que pour le chiffrement)
# ────────────────────────────────────────────────────────────────
def decrypt_aes256(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Déchiffre les données chiffrées (avec IV en tête) avec AES-256-CFB
    """
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]

    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()


# ────────────────────────────────────────────────────────────────
# Récupération, téléchargement et déchiffrement des images
# ────────────────────────────────────────────────────────────────
def fetch_and_decrypt_images(file_keys: str, doc_id: int) -> Tuple[bytes, bytes]:
    """
    - Télécharge deux images chiffrées depuis MinIO
    - Récupère la clé AES depuis PostgreSQL
    - Retourne (recto_bytes, verso_bytes) déchiffrées
    """
    # 1. Récupérer les deux clés MinIO (séparées par "|")
    keys = file_keys.split("|")
    if len(keys) != 2:
        raise ValueError("Le champ file_path ne contient pas exactement deux clés (recto|verso)")

    recto_key, verso_key = keys

    # 2. Télécharger les images chiffrées depuis MinIO
    recto_enc = s3_client.get_object(Bucket=MINIO_BUCKET, Key=recto_key)["Body"].read()
    verso_enc = s3_client.get_object(Bucket=MINIO_BUCKET, Key=verso_key)["Body"].read()

    # 3. Récupérer la clé AES depuis PostgreSQL
    db = SessionLocal()
    doc = db.query(Document).filter_by(id=doc_id).first()
    db.close()

    if not doc or not doc.vault_key_path:
        raise ValueError("Référence vers la clé AES introuvable dans Vault.")


    key = load_key_from_vault(doc.vault_key_path)


    # 4. Déchiffrer les deux images
    recto_bytes = decrypt_aes256(recto_enc, key)
    verso_bytes = decrypt_aes256(verso_enc, key)

    return recto_bytes, verso_bytes
