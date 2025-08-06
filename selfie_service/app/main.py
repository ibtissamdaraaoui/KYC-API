# ───────────────────────────────────────────────
# Imports standard & dépendances
# ───────────────────────────────────────────────
import os
import json
from datetime import datetime

from io import BytesIO
from app.vault_client import store_key_in_vault

# FastAPI et SQLAlchemy
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session

# Modules internes du microservice
from app import models
from app.database import SessionLocal, init_db


from app.database import SessionLocal, init_db
from app.models import Selfie
from app.schemas import SelfieResponse
from app.minio_client import s3_client, MINIO_BUCKET

# Kafka & chiffrement AES
from kafka import KafkaProducer
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# ───────────────────────────────────────────────
# 1) Initialisation de la base (tables) au démarrage
# ───────────────────────────────────────────────
init_db()  # Crée la table 'selfies' si elle n'existe pas


# ───────────────────────────────────────────────
# 2) Configuration Kafka
#    • Topic           : selfie_uploaded
#    • Broker par défaut: localhost:9092
# ───────────────────────────────────────────────
KAFKA_TOPIC  = "selfie_uploaded"
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)


# ───────────────────────────────────────────────
# 3) Initialisation FastAPI
# ───────────────────────────────────────────────
app = FastAPI(title="Selfie Service - KYC", version="1.0")


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
# 5) Endpoint POST /upload-selfie
#    • Reçoit selfie + kyc_case_id
#    • Vérifie format → chiffre → stocke MinIO
#    • Enregistre DB → envoie message Kafka
# ───────────────────────────────────────────────
@app.post("/upload-selfie", response_model=SelfieResponse)
async def upload_selfie(
    kyc_case_id: str = Form(...),
    selfie: UploadFile = File(...)
):
    print("➡️ Reçu selfie pour KYC ID:", kyc_case_id)

    # Vérification extension
    if not selfie.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Format invalide")

    # Génère clé AES
    encryption_key = os.urandom(32)
    print("➡️ Clé AES générée")

    vault_key_path = store_key_in_vault(kyc_case_id, encryption_key)
    print("➡️ Clé stockée dans Vault:", vault_key_path)

    raw_data = await selfie.read()
    encrypted = encrypt_file_aes256(raw_data, encryption_key)
    print("➡️ Chiffrement OK")

    s3_key = f"{datetime.utcnow().timestamp()}_{selfie.filename}"

    s3_client.put_object(
    bucket_name=MINIO_BUCKET,
    object_name=s3_key,
    data=BytesIO(encrypted),
    length=len(encrypted),
    metadata={"encrypted": "true", "algorithm": "AES-256"}
    )

    print("➡️ Upload MinIO OK")

    db: Session = SessionLocal()
    selfie_db = Selfie(
        kyc_case_id=kyc_case_id,
        file_key=s3_key,
        encryption_key_id=vault_key_path
    )
    db.add(selfie_db)
    db.commit()
    db.refresh(selfie_db)
    db.close()
    print("➡️ Sauvegarde DB OK")

    payload = {
        "id": selfie_db.id,
        "kyc_case_id": kyc_case_id,
        "file_key": s3_key,
        "created_at": datetime.utcnow().isoformat()
    }

    producer.send(KAFKA_TOPIC, payload)
    producer.flush()
    print("➡️ Message Kafka OK")

    return selfie_db
