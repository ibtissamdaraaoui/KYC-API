# ------------------ BLOC DE CONFIGURATION CENTRALE ------------------
import sys
from pathlib import Path
# Ajouter la racine du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))
from config import settings # Charge la configuration
# --------------------------------------------------------------------

import threading
from fastapi import FastAPI
from app import models
from app.database import engine
from app.router import case, proxy,auth
from app.kafka_consumer import consume_workflow_events# MODIFICATION
from app.database import init_db
# --- CORRECTION : Appeler la fonction d'initialisation contrôlée ---
init_db()

app = FastAPI(title="workflow_service")

@app.on_event("startup")
def on_startup():
    """Lance le consommateur Kafka dans un thread d'arrière-plan."""
    print("API starting up... Launching Kafka consumer thread.")
    consumer_thread = threading.Thread(
        target=consume_workflow_events,
        daemon=True  # Permet à l'application de quitter même si le thread tourne
    )
    consumer_thread.start()

# Routes
app.include_router(case.router, tags=["KYC Case"])
app.include_router(proxy.router, tags=["Proxy Upload"])
app.include_router(auth.router, tags=["Authentification"])