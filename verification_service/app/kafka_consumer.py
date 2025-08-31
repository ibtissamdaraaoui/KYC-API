# ------------------ BLOC DE CONFIGURATION CENTRALE ------------------
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))
from config import settings
from config.logging_config import setup_logging
import logging
setup_logging("verification_service")
# --------------------------------------------------------------------

import os
import json
import pprint
from kafka import KafkaConsumer, KafkaProducer
 

from app import database, models
from app.database import SessionLocal
from app.schemas import VerificationResultCreate
from app.crud import create_verification_result  # Appel de la fonction d’insertion
from app.processor import fetch_and_decrypt_images
from app.encryption_utils import encrypt_data 
from app.ocr_processor import run_ocr_on_image_bytes
from app.structuration_processor import process_structuration


# ─────────────── Paramètres Kafka (CORRIGÉE) ───────────────
# On lit toutes les variables depuis le .env SANS valeurs par défaut
KAFKA_CONSUMER_TOPIC = os.getenv("KAFKA_DOCUMENT_UPLOADED_TOPIC")
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID") # Assurez-vous d'avoir une variable KAFKA_GROUP_ID dans votre .env
KAFKA_SUCCESS_TOPIC = os.getenv("KAFKA_DOCUMENT_VERIFIED_TOPIC")
KAFKA_FAILURE_TOPIC = os.getenv("KAFKA_FAILURE_TOPIC")


# On vérifie que TOUTES les variables nécessaires sont bien présentes
required_vars = {
    "KAFKA_DOCUMENT_UPLOADED_TOPIC": KAFKA_CONSUMER_TOPIC,
    "KAFKA_BROKER": KAFKA_BROKER,
    "KAFKA_GROUP_ID": KAFKA_GROUP_ID,
    "KAFKA_DOCUMENT_VERIFIED_TOPIC": KAFKA_SUCCESS_TOPIC,
    "KAFKA_FAILURE_TOPIC": KAFKA_FAILURE_TOPIC
}
missing_vars = [key for key, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"ERREUR: Variables d'environnement Kafka manquantes : {', '.join(missing_vars)}")


# ─────────────── Initialisation du consommateur ───────────────
# On utilise maintenant la variable corrigée KAFKA_CONSUMER_TOPIC
consumer = KafkaConsumer(
    KAFKA_CONSUMER_TOPIC,
    bootstrap_servers=KAFKA_BROKER.split(","),
    group_id=KAFKA_GROUP_ID,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=False,
    session_timeout_ms=60000,
    max_poll_interval_ms=600000
)

# ─────────────── Initialisation du producteur ───────────────
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

logging.info(f"[Kafka] En écoute sur le topic '{KAFKA_CONSUMER_TOPIC}'...")

# ─────────────── Boucle d’écoute ───────────────
for message in consumer:
    payload = message.value
    doc_id = payload.get("id")
    file_keys = payload.get("file_path")
    kyc_case_id = payload.get("kyc_case_id")  # 

    logging.info("\n===== Nouveau message Kafka reçu =====")
    logging.info(f"ID Document     : {doc_id}")
    logging.info(f"KYC Case ID     : {kyc_case_id}")
    logging.info(f"Clés MinIO      : {file_keys}")
    logging.info("=========================================\n")

    try:
        # ────────── 1. Récupération & déchiffrement ──────────
        recto_bytes, verso_bytes = fetch_and_decrypt_images(file_keys, doc_id)

        # ────────── 2. OCR sur recto & verso ──────────
        recto_text = run_ocr_on_image_bytes(recto_bytes)
        verso_text = run_ocr_on_image_bytes(verso_bytes)

        recto_text_str = "\n".join(recto_text)
        verso_text_str = "\n".join(verso_text)

        logging.info(" Résultat OCR - Recto :")
        logging.info(recto_text_str or "[Aucun texte détecté]")
        logging.info("\n Résultat OCR - Verso :")
        logging.info(verso_text_str or "[Aucun texte détecté]")
        # ────────── 3. Structuration via Ollama ──────────
        rapport_validation = process_structuration(recto_text_str, verso_text_str)
        pprint.pprint(rapport_validation)

        # --- DÉBUT DE LA SECTION DE CHIFFREMENT ET SAUVEGARDE ---

        # On combine les textes bruts
        full_raw_text = recto_text_str + "\n" + verso_text_str

        # On convertit le rapport (dictionnaire) en chaîne de caractères JSON
        structured_data_as_json_string = json.dumps(rapport_validation)

        # On chiffre les deux chaînes de caractères
        encrypted_raw_text = encrypt_data(full_raw_text)
        encrypted_structured_data = encrypt_data(structured_data_as_json_string)

        # ────────── 4. Enregistrement base de données ──────────
        db = SessionLocal()

        # On crée l'objet Pydantic avec les données chiffrées (qui sont des strings)
        verification_data = VerificationResultCreate(
            document_id=doc_id,
            raw_text=encrypted_raw_text,
            structured_data=encrypted_structured_data, # C'est maintenant une chaîne, conforme au schéma
            status=rapport_validation.get("status_validation", "NON_VALIDÉ")
        )

        # Appeler la fonction CRUD
        create_verification_result(db, verification_data)
        
        db.close()

        logging.info("Résultat structuré stocké avec succès.\n")


        # ------------------------------------------------------------------
        # MODIFICATION: Logique d'aiguillage basée sur le statut
        # ------------------------------------------------------------------
        status = rapport_validation.get("status_validation", "NON_VALIDÉ")

        if status == "VALIDÉ":
            # --- CAS SUCCÈS ---
            logging.info(f"--> Statut VALIDÉ. Envoi du message au topic '{KAFKA_SUCCESS_TOPIC}'...")
            
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
            logging.info("--> Message de succès envoyé.")
            pprint.pprint(success_payload)

        else:
            # --- CAS ÉCHEC ---
            logging.info(f"--> Statut NON_VALIDÉ. Envoi du message au topic '{KAFKA_FAILURE_TOPIC}'...")

            # On envoie un payload riche en informations pour le débogage et la notification utilisateur
            failure_payload = {
                "kyc_case_id": kyc_case_id,
                "failed_service": "verification_service",
                "reason": rapport_validation.get("reason_for_status", "Raison inconnue"),
                "details": rapport_validation.get("errors_details", {})
            }
            producer.send(KAFKA_FAILURE_TOPIC, value=failure_payload)
            logging.info("--> Message d'échec envoyé.")
            pprint.pprint(failure_payload)

        producer.flush() # Forcer l'envoi
        logging.info("-" * 50)
         # ==========================================================
        # AJOUT CRUCIAL : On commit l'offset manuellement ICI
        # Cela dit à Kafka : "Le traitement de ce message est terminé avec succès.
        # Ne me le renvoyez plus."
        # ==========================================================
        consumer.commit()
        logging.info("Offset commité avec succès. En attente du prochain message.")

    except Exception as e:
        # Gérer les erreurs techniques (ex: MinIO inaccessible) en publiant aussi un échec
        logging.error(f" Erreur technique majeure lors du traitement du document {doc_id}: {e}")
        failure_payload = {
            "kyc_case_id": kyc_case_id,
            "failed_service": "verification_service",
            "reason": "TECHNICAL_ERROR",
            "details": {"error_message": str(e)}
        }
        producer.send(KAFKA_FAILURE_TOPIC, value=failure_payload)
        producer.flush()

 
