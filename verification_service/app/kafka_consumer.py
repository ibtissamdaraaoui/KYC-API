import os
import json
import pprint
from kafka import KafkaConsumer, KafkaProducer

from app import database, models
from app.database import SessionLocal
from app.schemas import VerificationResultCreate
from app.crud import create_verification_result  # Appel de la fonction d’insertion
from app.processor import fetch_and_decrypt_images
from app.ocr_processor import run_ocr_on_image_bytes
from app.structuration_processor import process_structuration

# ─────────────── Paramètres Kafka ───────────────
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "document_uploaded")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "verification_group")

# -------MODIFICATION: Ajout du topic pour le producteur --
KAFKA_SUCCESS_TOPIC = os.getenv("KAFKA_VERIFIED_TOPIC", "document_verified")
KAFKA_FAILURE_TOPIC = os.getenv("KAFKA_FAILURE_TOPIC", "kyc_case_failed")

# ─────────────── Initialisation du consommateur ───────────────
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER.split(","),
    group_id=KAFKA_GROUP_ID,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True
)

# MODIFICATION: Initialisation du producteur
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8") # Sérialiseur pour convertir le dict en JSON
)

print(f"[Kafka] En écoute sur le topic '{KAFKA_TOPIC}'...")

# ─────────────── Boucle d’écoute ───────────────
for message in consumer:
    payload = message.value
    doc_id = payload.get("id")
    file_keys = payload.get("file_path")
    kyc_case_id = payload.get("kyc_case_id")  # 

    print("\n===== Nouveau message Kafka reçu =====")
    print(f"ID Document     : {doc_id}")
    print(f"KYC Case ID     : {kyc_case_id}")
    print(f"Clés MinIO      : {file_keys}")
    print("=========================================\n")

    try:
        # ────────── 1. Récupération & déchiffrement ──────────
        recto_bytes, verso_bytes = fetch_and_decrypt_images(file_keys, doc_id)

        # ────────── 2. OCR sur recto & verso ──────────
        recto_text = run_ocr_on_image_bytes(recto_bytes)
        verso_text = run_ocr_on_image_bytes(verso_bytes)

        recto_text_str = "\n".join(recto_text)
        verso_text_str = "\n".join(verso_text)

        print(" Résultat OCR - Recto :")
        print(recto_text_str or "[Aucun texte détecté]")
        print("\n Résultat OCR - Verso :")
        print(verso_text_str or "[Aucun texte détecté]")

        # ────────── 3. Structuration via Ollama ──────────
        rapport_validation = process_structuration(recto_text_str, verso_text_str)
        pprint.pprint(rapport_validation)

        # ────────── 4. Enregistrement base de données ──────────
        db = SessionLocal()

        verification_data = VerificationResultCreate(
            document_id=doc_id, # C'est maintenant le champ principal
            raw_text=recto_text_str + "\n" + verso_text_str,
            structured_data=rapport_validation, # Passer le dictionnaire directement
            status=rapport_validation.get("status_validation", "NON_VALIDÉ")
        )
        
        # Appeler la fonction CRUD
        create_verification_result(db, verification_data)
        
        db.close()

        print("Résultat structuré stocké avec succès.\n")


        # ------------------------------------------------------------------
        # MODIFICATION: Logique d'aiguillage basée sur le statut
        # ------------------------------------------------------------------
        status = rapport_validation.get("status_validation", "NON_VALIDÉ")

        if status == "VALIDÉ":
            # --- CAS SUCCÈS ---
            print(f"--> Statut VALIDÉ. Envoi du message au topic '{KAFKA_SUCCESS_TOPIC}'...")
            
            keys = file_keys.split("|")
            recto_key, verso_key = keys if len(keys) == 2 else (None, None)

            success_payload = {
                "kyc_case_id": kyc_case_id,
                "document_id": doc_id,  
                "status": status,
                "document_locations": {
                    "recto_path": recto_key,
                    "verso_path": verso_key
                }
            }
            producer.send(KAFKA_SUCCESS_TOPIC, value=success_payload)
            print("--> Message de succès envoyé.")
            pprint.pprint(success_payload)

        else:
            # --- CAS ÉCHEC ---
            print(f"--> Statut NON_VALIDÉ. Envoi du message au topic '{KAFKA_FAILURE_TOPIC}'...")

            # On envoie un payload riche en informations pour le débogage et la notification utilisateur
            failure_payload = {
                "kyc_case_id": kyc_case_id,
                "failed_service": "verification_service",
                "reason": rapport_validation.get("reason_for_status", "Raison inconnue"),
                "details": rapport_validation.get("errors_details", {})
            }
            producer.send(KAFKA_FAILURE_TOPIC, value=failure_payload)
            print("--> Message d'échec envoyé.")
            pprint.pprint(failure_payload)

        producer.flush() # Forcer l'envoi
        print("-" * 50)

    except Exception as e:
        # Gérer les erreurs techniques (ex: MinIO inaccessible) en publiant aussi un échec
        print(f" Erreur technique majeure lors du traitement du document {doc_id}: {e}")
        failure_payload = {
            "kyc_case_id": kyc_case_id,
            "failed_service": "verification_service",
            "reason": "TECHNICAL_ERROR",
            "details": {"error_message": str(e)}
        }
        producer.send(KAFKA_FAILURE_TOPIC, value=failure_payload)
        producer.flush()

 
