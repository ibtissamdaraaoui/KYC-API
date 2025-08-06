# Fichier: matching_service/app/kafka_clients.py
import os
import json
import time
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import MatchingTask, Document, Selfie
from app.crud import get_or_create_task, update_task_with_document, update_task_with_selfie, create_matching_result
from app.processor.image_handler import fetch_and_decrypt_image

init_db()

KAFKA_BROKER = os.getenv("KAFKA_BROKER")
TOPIC_DOC_VERIFIED = os.getenv("KAFKA_DOCUMENT_VERIFIED_TOPIC")
TOPIC_SELFIE_UPLOADED = os.getenv("KAFKA_SELFIE_UPLOADED_TOPIC")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID")

def execute_matching_process(db: Session, task: MatchingTask):
    print(f"\n[{task.kyc_case_id}] DÉCLENCHEMENT DU PROCESSUS DE MATCHING COMPLET.")
    
    task.status = "PROCESSING"
    db.commit()

    try:
        doc_record = db.query(Document).filter_by(id=task.document_id).first()
        selfie_record = db.query(Selfie).filter_by(id=task.selfie_id).first()

        if not doc_record or not selfie_record:
            raise ValueError("Enregistrement document ou selfie introuvable en BDD.")

        decrypted_cin_bytes = fetch_and_decrypt_image(
            minio_file_key=doc_record.recto_path,
            object_type='document',
            object_id=doc_record.id
        )
        decrypted_selfie_bytes = fetch_and_decrypt_image(
            minio_file_key=selfie_record.file_key,
            object_type='selfie',
            object_id=selfie_record.id
        )

        if not decrypted_cin_bytes or not decrypted_selfie_bytes:
            raise Exception("Échec du déchiffrement d'une ou des deux images.")

        print(f"[{task.kyc_case_id}] Images déchiffrées. PRÊT POUR LE FACE MATCHING.")
        
        # --- BLOC À REMPLACER PAR LE VRAI FACE MATCHER ---
        # match_result = verify_faces_in_memory(decrypted_selfie_bytes, decrypted_cin_bytes)
        # is_match = match_result.get("verified", False)
        # distance = match_result.get("distance", 999.0)
        
        # Pour le test, on simule un succès
        is_match = True
        distance = 0.25
        # --- FIN DU BLOC DE SIMULATION ---

        result_data = {
            "kyc_case_id": task.kyc_case_id,
            "document_id": task.document_id,
            "selfie_id": task.selfie_id,
            "match_result": "MATCH" if is_match else "NO_MATCH",
            "distance": distance,
            "model_details": {"model": "VGG-Face", "detector": "mtcnn"}
        }
        create_matching_result(db, result_data)
        
        task.status = "COMPLETED"
        print(f"[{task.kyc_case_id}] Processus de matching terminé avec succès.")
        
    except Exception as e:
        print(f"[{task.kyc_case_id}] ERREUR CRITIQUE durant le matching : {e}")
        task.status = "FAILED"
    
    db.commit()

def consume_events():
    """
    Fonction principale qui écoute les messages Kafka, met à jour les tâches
    et déclenche le processus de matching.
    """
    
    # --- DÉBUT DU BLOC DE CODE MANQUANT ---
    
    consumer = None
    # Boucle pour tenter de se connecter à Kafka au démarrage.
    # C'est une bonne pratique pour la robustesse.
    while consumer is None:
        try:
            # On vérifie que les variables d'environnement ne sont pas vides
            if not all([KAFKA_BROKER, TOPIC_DOC_VERIFIED, TOPIC_SELFIE_UPLOADED, KAFKA_GROUP_ID]):
                print("❌ ERREUR: Une ou plusieurs variables d'environnement Kafka sont manquantes.")
                print("   Vérifiez KAFKA_BROKER, KAFKA_DOCUMENT_VERIFIED_TOPIC, KAFKA_SELFIE_UPLOADED_TOPIC, KAFKA_GROUP_ID")
                time.sleep(10)
                continue

            consumer = KafkaConsumer(
                TOPIC_DOC_VERIFIED,
                TOPIC_SELFIE_UPLOADED,
                bootstrap_servers=KAFKA_BROKER.split(","),
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest"
            )
            print(f"✅ Connecté à Kafka. En écoute sur les topics: '{TOPIC_DOC_VERIFIED}', '{TOPIC_SELFIE_UPLOADED}'...")
        
        except NoBrokersAvailable:
            print(f"❌ Kafka non disponible à '{KAFKA_BROKER}'. Nouvelle tentative dans 5 secondes...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Une erreur inattendue est survenue lors de la connexion à Kafka: {e}")
            time.sleep(5)

    # --- FIN DU BLOC DE CODE MANQUANT ---
    for message in consumer:
        payload = message.value
        kyc_case_id = payload.get("kyc_case_id")
        if not kyc_case_id: continue

        print(f"\n📩 Message reçu sur le topic '{message.topic}' pour {kyc_case_id}")

        db = SessionLocal()
        try:
            task = get_or_create_task(db, kyc_case_id)
            
            if message.topic == TOPIC_DOC_VERIFIED:
                update_task_with_document(db, task, payload["document_id"])
            elif message.topic == TOPIC_SELFIE_UPLOADED:
                update_task_with_selfie(db, task, payload["id"])
            
            db.refresh(task)
            if task.document_id and task.selfie_id and task.status == "PENDING":
                execute_matching_process(db, task)
        finally:
            db.close()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    consume_events()