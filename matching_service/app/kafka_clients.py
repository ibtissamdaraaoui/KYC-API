# Fichier: matching_service/app/kafka_clients.py
# ------------------ BLOC DE CONFIGURATION CENTRALE ------------------
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))
from config import settings
# --------------------------------------------------------------------

import os
import json
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from sqlalchemy.orm import Session
import numpy as np

# Imports de l'application
from app.database import SessionLocal, init_db
from app.models import MatchingTask, Document, Selfie
from app.crud import get_or_create_task, update_task_with_document, update_task_with_selfie, create_matching_result
from app.processor.image_handler import fetch_and_decrypt_image
from app.processor.face_matcher import extract_face_from_image, verify_faces

# Initialisation BDD
init_db()
# --- CONFIGURATION KAFKA (VERSION FINALE CORRIGÉE ET ROBUSTE) ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
TOPIC_DOC_VERIFIED = os.getenv("KAFKA_DOCUMENT_VERIFIED_TOPIC")
TOPIC_SELFIE_UPLOADED = os.getenv("KAFKA_SELFIE_UPLOADED_TOPIC")
KAFKA_GROUP_ID = os.getenv("KAFKA_MATCHING_GROUP_ID")  # On utilise un nom spécifique
KAFKA_MATCHING_SUCCESS_TOPIC = os.getenv("KAFKA_MATCHING_SUCCESS_TOPIC")
KAFKA_FAILURE_TOPIC = os.getenv("KAFKA_FAILURE_TOPIC")

# Vérification "Fail-Fast" pour s'assurer que TOUT est configuré
required_vars = {
    "KAFKA_BROKER": KAFKA_BROKER,
    "KAFKA_DOCUMENT_VERIFIED_TOPIC": TOPIC_DOC_VERIFIED,
    "KAFKA_SELFIE_UPLOADED_TOPIC": TOPIC_SELFIE_UPLOADED,
    "KAFKA_MATCHING_GROUP_ID": KAFKA_GROUP_ID,
    "KAFKA_MATCHING_SUCCESS_TOPIC": KAFKA_MATCHING_SUCCESS_TOPIC,
    "KAFKA_FAILURE_TOPIC": KAFKA_FAILURE_TOPIC
}
missing_vars = [key for key, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"ERREUR: Variables d'environnement Kafka manquantes pour le matching_service : {', '.join(missing_vars)}")


# --- INITIALISATION DU PRODUCTEUR KAFKA ---
# On le crée une seule fois pour être réutilisé
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)


def convert_numpy_to_native(obj):
    """
    Convertit récursivement les types NumPy en types natifs Python pour la sérialisation JSON.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_native(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_native(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_native(item) for item in obj)
    else:
        return obj


def execute_matching_process(db: Session, task: MatchingTask):
    """
    Exécute le processus de matching et retourne le verdict et les détails.
    Ne fait plus de commit elle-même.
    """
    print("\n" + "="*50)
    print(f"▶️  [{task.kyc_case_id}] DÉCLENCHEMENT DU PROCESSUS DE FACE MATCHING")
    print("="*50)
    
    task.status = "PROCESSING"

    final_verdict = "ERROR"
    final_details = {}

    try:
        # 1. Récupérer les enregistrements
        print(f"[{task.kyc_case_id}] 1. Récupération des métadonnées (Doc ID: {task.document_id}, Selfie ID: {task.selfie_id})...")
        doc_record = db.query(Document).filter_by(id=task.document_id).first()
        selfie_record = db.query(Selfie).filter_by(id=task.selfie_id).first()
        if not doc_record or not selfie_record:
            raise ValueError("Enregistrement document ou selfie introuvable en BDD.")
        print(f"[{task.kyc_case_id}] ... Métadonnées OK.")

        # 2. Déchiffrer les images
        print(f"[{task.kyc_case_id}] 2. Déchiffrement des images...")
        decrypted_cin_bytes = fetch_and_decrypt_image(
            minio_file_key=doc_record.recto_path, object_type='document', object_id=doc_record.id)
        decrypted_selfie_bytes = fetch_and_decrypt_image(
            minio_file_key=selfie_record.file_key, object_type='selfie', object_id=selfie_record.id)
        if not decrypted_cin_bytes or not decrypted_selfie_bytes:
            raise Exception("Échec du déchiffrement d'une ou des deux images.")
        print(f"[{task.kyc_case_id}] ... Déchiffrement OK.")

        # 3. Extraire le visage de la CIN
        print(f"[{task.kyc_case_id}] 3. Extraction du visage depuis la CIN...")
        extracted_face_bytes = extract_face_from_image(decrypted_cin_bytes)
        if not extracted_face_bytes:
            raise ValueError("Aucun visage n'a pu être extrait de l'image de la CIN.")
        print(f"[{task.kyc_case_id}] ... Extraction du visage OK.")

        # 4. Comparer le visage extrait et le selfie
        print(f"[{task.kyc_case_id}] 4. Comparaison du visage extrait avec le selfie...")
        match_result = verify_faces(
            img1_bytes=extracted_face_bytes, img2_bytes=decrypted_selfie_bytes)
        print(f"[{task.kyc_case_id}] ... Comparaison OK.")
        final_details = match_result

        # 5. Déterminer le verdict final
        is_match = match_result.get("verified", False)
        final_verdict = "MATCH" if is_match else "NO_MATCH"
        task.status = "COMPLETED"
        print(f"✔️  [{task.kyc_case_id}] Processus de matching terminé. Verdict final: {final_verdict}")
        
    except Exception as e:
        print(f"❌ [{task.kyc_case_id}] ERREUR CRITIQUE durant le matching : {e}")
        task.status = "FAILED"
        final_verdict = "ERROR"
        final_details = {"error_message": str(e)}
    
    # Prépare les données pour l'enregistrement BDD
    cleaned_details = convert_numpy_to_native(final_details)
    result_data = {
        "kyc_case_id": task.kyc_case_id,
        "document_id": task.document_id or -1,
        "selfie_id": task.selfie_id or -1,
        "match_result": final_verdict,
        "distance": cleaned_details.get("distance"),
        "model_details": cleaned_details 
    }
    create_matching_result(db, result_data) # Ajoute à la session BDD, mais ne commit pas
    
    return final_verdict, cleaned_details


def consume_events():
    """
    Fonction principale qui écoute les messages Kafka, met à jour les tâches
    et déclenche le processus de matching.
    """
    consumer = None
    while consumer is None:
        try:
            if not all([KAFKA_BROKER, TOPIC_DOC_VERIFIED, TOPIC_SELFIE_UPLOADED, KAFKA_GROUP_ID]):
                print("❌ ERREUR: Variables d'environnement Kafka manquantes.")
                time.sleep(10)
                continue

            consumer = KafkaConsumer(
                TOPIC_DOC_VERIFIED, TOPIC_SELFIE_UPLOADED,
                bootstrap_servers=KAFKA_BROKER.split(","),
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=False,
                max_poll_interval_ms=600000 
            )
            print(f"✅ Connecté à Kafka. En écoute sur les topics: '{TOPIC_DOC_VERIFIED}', '{TOPIC_SELFIE_UPLOADED}'...")
        except NoBrokersAvailable:
            print(f"❌ Kafka non disponible à '{KAFKA_BROKER}'. Nouvelle tentative dans 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Erreur de connexion à Kafka: {e}")
            time.sleep(5)

    for message in consumer:
        payload = message.value
        kyc_case_id = payload.get("kyc_case_id")
        if not kyc_case_id: 
            consumer.commit()
            continue

        print(f"\n📩 Message reçu sur le topic '{message.topic}' pour {kyc_case_id}")

        db = SessionLocal()
        try:
            task = get_or_create_task(db, kyc_case_id)
            
            if message.topic == TOPIC_DOC_VERIFIED:
                update_task_with_document(db, task, payload["document_id"])
            elif message.topic == TOPIC_SELFIE_UPLOADED:
                update_task_with_selfie(db, task, payload["id"])
            
            db.commit() # Commit de la mise à jour de la tâche
            db.refresh(task)
            
            if task.document_id and task.selfie_id and task.status == "PENDING":
                verdict, details = execute_matching_process(db, task)
                
                db.commit() # Commit du résultat du matching
                print(f"[{kyc_case_id}] Résultat du matching commité en BDD.")

                # Envoi du message de statut au workflow_service
                if verdict == "MATCH":
                    print(f"--> Statut MATCH. Envoi du message au topic '{KAFKA_MATCHING_SUCCESS_TOPIC}'...")
                    success_payload = {
                        "kyc_case_id": kyc_case_id, "status": "MATCHING_SUCCESS",
                        "details": {"distance": details.get("distance"), "model": details.get("model")}
                    }
                    producer.send(KAFKA_MATCHING_SUCCESS_TOPIC, value=success_payload)
                else:
                    print(f"--> Statut {verdict}. Envoi du message au topic '{KAFKA_FAILURE_TOPIC}'...")
                    failure_payload = {
                        "kyc_case_id": kyc_case_id, "failed_service": "matching_service",
                        "reason": f"FACE_MATCHING_{verdict}", "details": details 
                    }
                    producer.send(KAFKA_FAILURE_TOPIC, value=failure_payload)

                producer.flush()
                print("--> Message de statut envoyé au workflow_service.")
            
            consumer.commit()

        except Exception as e:
            print(f"❌ ERREUR MAJEURE DANS LA BOUCLE KAFKA pour le cas {kyc_case_id}: {e}")
            db.rollback()
            time.sleep(5)
        finally:
            db.close()

if __name__ == "__main__":
    
    consume_events()