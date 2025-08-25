# Fichier: workflow_service/app/kafka_consumer.py



import os
import json
import pprint
import threading
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

# Import des modules de votre application
from app.database import SessionLocal
from app.crud import update_kyc_case_status
from app.models import KycCaseStatus

# ──────────────────────────────────────────────────────────────────
#  FONCTION PRINCIPALE DE CONSOMMATION
# ──────────────────────────────────────────────────────────────────
def consume_workflow_events():
    thread_id = threading.get_ident()
    print(f"[Thread-{thread_id}] Démarrage du consommateur Kafka pour le workflow_service...")

    # ─────────────── Paramètres Kafka (CORRIGÉE) ───────────────
    KAFKA_BROKER = os.getenv("KAFKA_BROKER")
    KAFKA_FAILURE_TOPIC = os.getenv("KAFKA_FAILURE_TOPIC")
    KAFKA_MATCHING_SUCCESS_TOPIC = os.getenv("KAFKA_MATCHING_SUCCESS_TOPIC")
    # Utiliser une clé cohérente avec les autres services si possible
    KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "workflow_group") # Garder une valeur par défaut ici est acceptable si non critique

    # --- VÉRIFICATION CRITIQUE ---
    required_vars = {
        "KAFKA_BROKER": KAFKA_BROKER,
        "KAFKA_FAILURE_TOPIC": KAFKA_FAILURE_TOPIC,
        "KAFKA_MATCHING_SUCCESS_TOPIC": KAFKA_MATCHING_SUCCESS_TOPIC,
        "KAFKA_GROUP_ID": KAFKA_GROUP_ID
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"ERREUR: Variables d'environnement Kafka manquantes pour le workflow_service : {', '.join(missing_vars)}")

    # ─────────────── Initialisation du consommateur ───────────────
    consumer = None
    while consumer is None:
        try:
            # On écoute maintenant sur DEUX topics
            topics_to_consume = [KAFKA_FAILURE_TOPIC, KAFKA_MATCHING_SUCCESS_TOPIC]
            
            consumer = KafkaConsumer(
                *topics_to_consume, # L'étoile dépaquette la liste des topics
                bootstrap_servers=KAFKA_BROKER.split(","),
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                # On passe au commit manuel pour plus de robustesse
                enable_auto_commit=False,
            )
            print(f"[Thread-{thread_id}] Connecté à Kafka. En écoute sur les topics: {topics_to_consume}...")
        except NoBrokersAvailable:
            print(f"[Thread-{thread_id}] [ERREUR] Impossible de se connecter à Kafka. Nouvelle tentative dans 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[Thread-{thread_id}] [ERREUR] Erreur de connexion à Kafka: {e}")
            time.sleep(5)
            
    # ─────────────── Boucle d’écoute principale ───────────────
    try:
        for message in consumer:
            payload = message.value
            kyc_case_id = payload.get("kyc_case_id")

            if not kyc_case_id:
                print(f"[Thread-{thread_id}] [AVERTISSEMENT] Message reçu sans kyc_case_id. Message ignoré.")
                consumer.commit() # On commit pour ne pas le relire
                continue

            db = SessionLocal()
            try:
                # --- LOGIQUE D'AIGUILLAGE BASÉE SUR LE TOPIC ---
                if message.topic == KAFKA_FAILURE_TOPIC:
                    # --- GESTION DES ÉCHECS ---
                    print("\n" + "="*60)
                    print(f"[Thread-{thread_id}] Message d'ÉCHEC reçu")
                    print(f"Topic: {message.topic} | KYC Case ID: {kyc_case_id}")
                    pprint.pprint(payload)
                    print("="*60 + "\n")
                    
                    reason = payload.get("reason", "Échec inconnu")
                    details = payload.get("details", {})
                    failed_service = payload.get("failed_service", "service_inconnu")
                    
                    full_reason = f"Service: {failed_service} - Raison: {reason}"
                    if details:
                        # On s'assure que details est bien un dict avant de le dumper
                        details_str = json.dumps(details) if isinstance(details, dict) else str(details)
                        full_reason += f" - Détails: {details_str}"

                    update_kyc_case_status(
                        db=db,
                        kyc_case_id=kyc_case_id,
                        status=KycCaseStatus.FAILED,
                        reason=full_reason[:255]
                    )
                    print(f"-> Cas KYC '{kyc_case_id}' mis à jour avec le statut 'FAILED'.")

                elif message.topic == KAFKA_MATCHING_SUCCESS_TOPIC:
                    # --- GESTION DES SUCCÈS DE MATCHING ---
                    print("\n" + "="*60)
                    print(f"[Thread-{thread_id}] Message de SUCCÈS de matching reçu")
                    print(f"Topic: {message.topic} | KYC Case ID: {kyc_case_id}")
                    pprint.pprint(payload)
                    print("="*60 + "\n")

                    # Le matching est réussi, on met à jour le statut pour passer à l'étape suivante.
                    # Ex: PENDING_FINAL_REVIEW ou directement COMPLETED si c'est la fin.
                    update_kyc_case_status(
                        db=db,
                        kyc_case_id=kyc_case_id,
                        status=KycCaseStatus.COMPLETED, # Ou un autre statut de succès
                        reason="Processus KYC terminé avec succès après un face-matching positif."
                    )
                    print(f"-> Cas KYC '{kyc_case_id}' mis à jour avec le statut 'COMPLETED'.")

                # 1. Commit de la transaction en base de données
                db.commit()
                # 2. Commit de l'offset Kafka
                consumer.commit()

            except Exception as e:
                print(f"[Thread-{thread_id}] [ERREUR] Erreur lors du traitement du message pour '{kyc_case_id}': {e}")
                db.rollback()
            finally:
                db.close()
                
    except Exception as e:
        print(f"[Thread-{thread_id}] [ERREUR FATALE] Le consommateur Kafka a rencontré une erreur majeure: {e}")
    finally:
        if consumer:
            consumer.close()
        print(f"[Thread-{thread_id}] Consommateur Kafka arrêté.")