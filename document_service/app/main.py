# ------------------ BLOC DE CONFIGURATION CENTRALE ------------------
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))
from config import settings
from config.logging_config import setup_logging
import logging
setup_logging("document_service")
# --------------------------------------------------------------------

# ───────────────────────────────────────────────
# Imports standard & dépendances
# ───────────────────────────────────────────────
import os
import json
import base64
from datetime import datetime
from app.vault_client import store_key_in_vault

# FastAPI et SQLAlchemy
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session

# Modules internes du microservice
from app.database import SessionLocal, init_db
from app.models import Document
from app.schemas import DocumentResponse
from app.minio_client import s3_client, MINIO_BUCKET

# Kafka & chiffrement AES
from kafka import KafkaProducer
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# ───────────────────────────────────────────────
# 1) Initialisation de la base (tables) au démarrage
# ───────────────────────────────────────────────
init_db()

# ───────────────────────────────────────────────
# 2) Configuration Kafka (CORRIGÉE)
#    • Les valeurs proviennent maintenant du .env central
# ───────────────────────────────────────────────
KAFKA_TOPIC = os.getenv("KAFKA_DOCUMENT_UPLOADED_TOPIC")
KAFKA_BROKER = os.getenv("KAFKA_BROKER")

# Vérification pour la robustesse (fail-fast)
if not KAFKA_TOPIC or not KAFKA_BROKER:
    raise ValueError("Les variables d'environnement KAFKA_DOCUMENT_UPLOADED_TOPIC ou KAFKA_BROKER sont manquantes.")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# ───────────────────────────────────────────────
# 3) Initialisation FastAPI
# ───────────────────────────────────────────────
app = FastAPI(title="Document Service - KYC", version="1.0")


# ───────────────────────────────────────────────
# 4) Fonction utilitaire : chiffrement AES-256 en mémoire
#    • Retour: IV + données chiffrées
# ───────────────────────────────────────────────
def encrypt_file_aes256(file_data: bytes, key: bytes) -> bytes:
    iv = os.urandom(16)  # vecteur d'initialisation aléatoire
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return iv + encryptor.update(file_data) + encryptor.finalize()


# ───────────────────────────────────────────────
# 5) Endpoint POST /upload
#    • Reçoit recto & verso + kyc_case_id
#    • Vérifie formats → chiffre → stocke MinIO
#    • Enregistre DB   → envoie message Kafka
# ───────────────────────────────────────────────
@app.post("/upload", response_model=DocumentResponse)
async def upload_cin_images(
    kyc_case_id: str = Form(...),
    recto: UploadFile   = File(...),
    verso: UploadFile   = File(...)
):
    # 5-1. Vérification des extensions
    for img in (recto, verso):
        if not img.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(
                status_code=400,
                detail="Formats acceptés : .jpg, .jpeg, .png"
            )

    # 5-2. Génération d'une clé AES-256 aléatoire
    encryption_key = os.urandom(32) # 32 octets = 256 bits
    vault_key_path = store_key_in_vault(encryption_key, kyc_case_id)

    # 5-3. Boucle sur les deux images pour :
    #      a) lire le contenu
    #      b) chiffrer
    #      c) envoyer sur MinIO
    file_keys = []
    for image in (recto, verso):
        raw_data = await image.read()
        encrypted = encrypt_file_aes256(raw_data, encryption_key) 


        # Clé unique dans MinIO : timestamp + nom du fichier original
        s3_key = f"{datetime.utcnow().timestamp()}_{image.filename}"
        file_keys.append(s3_key)

        # Upload dans MinIO
        try:
            s3_client.put_object(
                Bucket=MINIO_BUCKET,
                Key=s3_key,
                Body=encrypted,
                Metadata={"encrypted": "true", "algorithm": "AES-256"}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur MinIO : {e}")

    # 5-4. Sauvegarde de la ligne dans PostgreSQL
    db: Session = SessionLocal()
    # --- MODIFIÉ ---
    doc = Document(
        kyc_case_id=kyc_case_id,
        recto_path=file_keys[0], # Plus clair
        verso_path=file_keys[1],
        vault_key_path=vault_key_path
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()

    # 5-5. Construction & envoi du message Kafka
    # --- MODIFIÉ ---
    payload = {
        "id": doc.id,
        "kyc_case_id": kyc_case_id,
        "file_path": f"{doc.recto_path}|{doc.verso_path}",
        "upload_time": doc.created_at.isoformat()
    }
    try:
        producer.send(KAFKA_TOPIC, payload)
        producer.flush()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Kafka : {e}")

    return doc
