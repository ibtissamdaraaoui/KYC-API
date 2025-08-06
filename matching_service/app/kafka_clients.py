# Fichier: matching_service/app/kafka_clients.py

import os
import json
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

# Imports depuis notre application
from app.database import SessionLocal, init_db
from app.models import MatchingTask
from app.crud import get_or_create_task, update_task_with_doc_info, update_task_with_selfie_info
from app.processor.image_handler import fetch_and_decrypt_image

# --- Initialisation de la BDD au démarrage ---
init_db()

# --- Configuration Kafka ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
TOPIC_DOC_VERIFIED = os.getenv("KAFKA_DOCUMENT_VERIFIED_TOPIC")
TOPIC_SELFIE_UPLOADED = os.getenv("KAFKA_SELFIE_UPLOADED_TOPIC")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID")

def processing_function_for_test(kyc_case_id: str):
    """
    Fonction de test qui déchiffre les images et confirme leur réception en mémoire.
    AUCUN FICHIER N'EST SAUVEGARDÉ SUR LE DISQUE.
    """
    print(f"\n[{kyc_case_id}] DÉCLENCHEMENT DU TRAITEMENT DE DÉCHIFFREMENT EN MÉMOIRE.")
    db = SessionLocal()
    task = db.query(MatchingTask).filter_by(kyc_case_id=kyc_case_id).first()
    
    if not (task and task.recto_path and task.selfie_path):
        print(f"[{kyc_case_id}] ERREUR : Tâche ou chemins manquants en BDD.")
        db.close()
        return

    try:
        # --- Étape 1 : Déchiffrer la CIN en mémoire ---
        print(f"[{kyc_case_id}] Traitement de la CIN (ID: {task.document_id})...")
        decrypted_cin_bytes = fetch_and_decrypt_image(
            minio_file_key=task.recto_path,
            object_type='document',
            object_id=task.document_id
        )
        if decrypted_cin_bytes:
            # Confirmation en mémoire, sans sauvegarde
            print(f"[{kyc_case_id}] SUCCÈS : CIN déchiffrée en mémoire ({len(decrypted_cin_bytes)} bytes reçus).")
        else:
            print(f"[{kyc_case_id}] ÉCHEC : Impossible de déchiffrer la CIN.")
            db.close()
            return # Arrêt du processus si la CIN est manquante

        # --- Étape 2 : Déchiffrer le Selfie en mémoire ---
        print(f"[{kyc_case_id}] Traitement du Selfie (ID: {task.selfie_id})...")
        decrypted_selfie_bytes = fetch_and_decrypt_image(
            minio_file_key=task.selfie_path,
            object_type='selfie',
            object_id=task.selfie_id
        )
        if decrypted_selfie_bytes:
            # Confirmation en mémoire, sans sauvegarde
            print(f"[{kyc_case_id}] SUCCÈS : Selfie déchiffré en mémoire ({len(decrypted_selfie_bytes)} bytes reçus).")
        else:
            print(f"[{kyc_case_id}] ÉCHEC : Impossible de déchiffrer le selfie.")

        print(f"[{kyc_case_id}] Phase de déchiffrement terminée. Les données sont en RAM, prêtes pour le matching.")

    except Exception as e:
        print(f"[{kyc_case_id}] Échec du processus de test de déchiffrement : {e}")
    finally:
        db.close()

def consume_events():
    """
    Fonction principale qui écoute les messages Kafka et orchestre le flux.
    """
    consumer = None
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                TOPIC_DOC_VERIFIED,
                TOPIC_SELFIE_UPLOADED,
                bootstrap_servers=KAFKA_BROKER.split(","),
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest"
            )
            print(f"✅ Connecté à Kafka. En écoute sur les topics...")
        except NoBrokersAvailable:
            print("❌ Kafka non disponible. Nouvelle tentative dans 5 secondes...")
            time.sleep(5)

    for message in consumer:
        payload = message.value
        kyc_case_id = payload.get("kyc_case_id")
        if not kyc_case_id: continue

        print(f"\n📩 Message reçu sur le topic '{message.topic}' pour le cas {kyc_case_id}")

        db = SessionLocal()
        try:
            task = get_or_create_task(db, kyc_case_id)
            
            if message.topic == TOPIC_DOC_VERIFIED:
                doc_id = payload.get("document_id")
                recto_path = payload.get("document_locations", {}).get("recto_path")
                if doc_id and recto_path:
                    update_task_with_doc_info(db, task, doc_id, recto_path)

            elif message.topic == TOPIC_SELFIE_UPLOADED:
                selfie_id = payload.get("id")
                selfie_path = payload.get("file_key")
                if selfie_id and selfie_path:
                    update_task_with_selfie_info(db, task, selfie_id, selfie_path)
            
            db.refresh(task) 
            if task.document_verified_received and task.selfie_uploaded_received:
                processing_function_for_test(kyc_case_id)
        finally:
            db.close()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    consume_events()