import os
import json
import pprint
import threading # On importe threading pour avoir accès à l'ID du thread dans les logs
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
def consume_failure_messages():
    """
    Cette fonction s'exécute dans un thread d'arrière-plan et écoute en continu
    le topic Kafka des échecs pour mettre à jour l'état des cas KYC.
    """
    thread_id = threading.get_ident()
    print(f"[Thread-{thread_id}] Démarrage du consommateur Kafka pour le workflow_service...")

    # ─────────────── Paramètres Kafka ───────────────
    # Utilisation de variables d'environnement pour plus de flexibilité
    KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
    KAFKA_FAILURE_TOPIC = os.getenv("KAFKA_FAILURE_TOPIC", "kyc_case_failed")
    KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID_WORKFLOW", "workflow_group")

    # ─────────────── Initialisation du consommateur avec gestion des erreurs de connexion ───────────────
    consumer = None
    # Boucle pour tenter de se connecter à Kafka au démarrage.
    # C'est utile dans un environnement Docker où Kafka peut démarrer après ce service.
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                KAFKA_FAILURE_TOPIC,
                bootstrap_servers=KAFKA_BROKER.split(","),
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",  # Traite les messages manqués si le service était éteint
                enable_auto_commit=True,
                # Délai avant de considérer une reconnexion comme échouée
                reconnect_backoff_ms=1000, 
                # Temps d'attente maximum pour une requête au broker
                request_timeout_ms=40000 
            )
            print(f"[Thread-{thread_id}] Connecté à Kafka. En écoute sur le topic '{KAFKA_FAILURE_TOPIC}'...")
        except NoBrokersAvailable:
            print(f"[Thread-{thread_id}] [ERREUR] Impossible de se connecter aux brokers Kafka à '{KAFKA_BROKER}'. Nouvelle tentative dans 5 secondes...")
            time.sleep(5)
            
    # ─────────────── Boucle d’écoute principale ───────────────
    try:
        for message in consumer:
            payload = message.value
            
            print("\n" + "="*60)
            print(f"[Thread-{thread_id}] Message d'échec reçu par le Workflow Service")
            print(f"Topic: {message.topic} | Partition: {message.partition} | Offset: {message.offset}")
            pprint.pprint(payload)
            print("="*60 + "\n")
            
            kyc_case_id = payload.get("kyc_case_id")
            reason = payload.get("reason", "Échec inconnu")
            details = payload.get("details", {})
            failed_service = payload.get("failed_service", "service_inconnu")

            if not kyc_case_id:
                print(f"[Thread-{thread_id}] [AVERTISSEMENT] Message d'échec reçu sans kyc_case_id. Message ignoré.")
                continue

            # Utilisation d'une session de base de données pour chaque message
            db = SessionLocal()
            try:
                # Formatter une raison claire pour la BDD
                full_reason = f"Service: {failed_service} - Raison: {reason}"
                # On ajoute les détails s'ils existent et ne sont pas vides
                if details:
                    full_reason += f" - Détails: {json.dumps(details)}"

                # Mettre à jour le cas en base de données avec le statut FAILED
                update_kyc_case_status(
                    db=db,
                    kyc_case_id=kyc_case_id,
                    status=KycCaseStatus.FAILED,
                    reason=full_reason[:255] # Tronquer pour s'adapter à un VARCHAR(255) si besoin
                )
                
                print(f"[Thread-{thread_id}] Le processus pour le cas '{kyc_case_id}' a été marqué comme ÉCHOUÉ.")

            except Exception as e:
                print(f"[Thread-{thread_id}] [ERREUR] Erreur lors de la mise à jour BDD pour le cas '{kyc_case_id}': {e}")
            finally:
                # Toujours fermer la session BDD, même en cas d'erreur
                db.close()
                
    except Exception as e:
        # Gère les erreurs globales du consommateur (rare, mais possible)
        print(f"[Thread-{thread_id}] [ERREUR FATALE] Le consommateur Kafka a rencontré une erreur majeure: {e}")
    finally:
        # S'assurer de fermer la connexion au consommateur proprement
        if consumer:
            consumer.close()
        print(f"[Thread-{thread_id}] Consommateur Kafka arrêté.")