import threading
from fastapi import FastAPI
from app import models
from app.database import engine
from app.router import case, proxy
from app.kafka_consumer import consume_failure_messages # MODIFICATION
from app.database import init_db
# --- CORRECTION : Appeler la fonction d'initialisation contrôlée ---
init_db()

app = FastAPI(title="workflow_service")

@app.on_event("startup")
def on_startup():
    """Lance le consommateur Kafka dans un thread d'arrière-plan."""
    print("API starting up... Launching Kafka consumer thread.")
    consumer_thread = threading.Thread(
        target=consume_failure_messages,
        daemon=True  # Permet à l'application de quitter même si le thread tourne
    )
    consumer_thread.start()

# Routes
app.include_router(case.router, prefix="/kyc-case", tags=["KYC Case"])
app.include_router(proxy.router, prefix="/proxy", tags=["Proxy Upload"])