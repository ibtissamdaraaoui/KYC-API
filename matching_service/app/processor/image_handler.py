# Fichier: matching_service/app/processor/image_handler.py

import os
from typing import Optional
from sqlalchemy.orm import Session

# --- Imports depuis les modules de notre propre service ---
# (MODIFIÉ) Importer les noms des buckets au lieu d'un seul bucket
from ..minio_client import s3_client, MINIO_DOCS_BUCKET, MINIO_SELFIES_BUCKET
from ..vault_client import load_key_from_vault
from ..database import SessionLocal
from ..models import Document, Selfie

# --- Imports pour le déchiffrement ---
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# ──────────────────────────────────────────────────────────────────
#  Fonction utilitaire privée de déchiffrement (INCHANGÉE)
# ──────────────────────────────────────────────────────────────────
def _decrypt_aes256(encrypted_data: bytes, key: bytes) -> bytes:
    if len(encrypted_data) <= 16:
        raise ValueError("Données chiffrées invalides : taille inférieure ou égale à 16 bytes.")
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()

# ──────────────────────────────────────────────────────────────────
#  Fonctions privées pour retrouver le chemin Vault via la BDD (INCHANGÉES)
# ──────────────────────────────────────────────────────────────────
def _get_vault_path_for_document(db: Session, doc_id: int) -> Optional[str]:
    print(f"   - [DB Query] Recherche du chemin Vault pour le document ID: {doc_id}")
    document_record = db.query(Document).filter_by(id=doc_id).first()
    if document_record and document_record.vault_key_path:
        print(f"   - [DB Query] Chemin Vault trouvé: {document_record.vault_key_path}")
        return document_record.vault_key_path
    print(f"   - [DB Query] Aucun enregistrement trouvé pour le document ID: {doc_id}")
    return None

def _get_vault_path_for_selfie(db: Session, selfie_id: int) -> Optional[str]:
    print(f"   - [DB Query] Recherche du chemin Vault pour le selfie ID: {selfie_id}")
    selfie_record = db.query(Selfie).filter_by(id=selfie_id).first()
    if selfie_record and selfie_record.encryption_key_id:
        print(f"   - [DB Query] Chemin Vault trouvé: {selfie_record.encryption_key_id}")
        return selfie_record.encryption_key_id
    print(f"   - [DB Query] Aucun enregistrement trouvé pour le selfie ID: {selfie_id}")
    return None


# ──────────────────────────────────────────────────────────────────
#  Fonction Publique Principale (MODIFIÉE)
# ──────────────────────────────────────────────────────────────────
def fetch_and_decrypt_image(
    minio_file_key: str,
    object_type: str,  # Doit être 'document' ou 'selfie'
    object_id: int
) -> Optional[bytes]:
    """
    Orchestre le processus complet pour récupérer une image, en sélectionnant le bon bucket MinIO.
    """
    if not all([minio_file_key, object_type, object_id]):
        print("[HANDLER_ERROR] Appel invalide : informations manquantes (clé MinIO, type ou ID).")
        return None

    print(f"-> [Image Handler] Démarrage du processus pour {object_type} ID {object_id}...")
    
    db = SessionLocal()
    try:
        # --- Étape 1 : Obtenir le chemin Vault ET déterminer le bucket MinIO ---
        vault_key_path = None
        target_bucket = None  # Variable pour stocker le nom du bucket à utiliser

        if object_type == 'document':
            vault_key_path = _get_vault_path_for_document(db, object_id)
            target_bucket = MINIO_DOCS_BUCKET
        elif object_type == 'selfie':
            vault_key_path = _get_vault_path_for_selfie(db, object_id)
            target_bucket = MINIO_SELFIES_BUCKET
        else:
            raise ValueError(f"Type d'objet inconnu : '{object_type}'. Doit être 'document' ou 'selfie'.")
        
        if not vault_key_path:
            raise ValueError(f"Impossible de trouver le chemin de la clé Vault pour {object_type} ID {object_id}.")

        # --- Étape 2 : Télécharger depuis le bon bucket MinIO ---
        print(f"   - [MinIO] Téléchargement du fichier '{minio_file_key}' depuis le bucket '{target_bucket}'...")
        s3_object = s3_client.get_object(Bucket=target_bucket, Key=minio_file_key)
        encrypted_bytes = s3_object["Body"].read()
        print(f"   - [MinIO] Téléchargement terminé ({len(encrypted_bytes)} bytes).")

        # --- Étape 3 : Récupérer la clé depuis Vault ---
        decryption_key = load_key_from_vault(vault_key_path)

        # --- Étape 4 : Déchiffrer les données ---
        print("   - [Crypto] Déchiffrement des données de l'image...")
        decrypted_bytes = _decrypt_aes256(encrypted_bytes, decryption_key)
        
        print(f"-> [Image Handler] SUCCÈS : L'image pour {object_type} ID {object_id} est prête.")
        return decrypted_bytes

    except Exception as e:
        print(f"-> [Image Handler] ERREUR : Échec du processus pour {object_type} ID {object_id}. Erreur : {e}")
        return None
    finally:
        db.close()