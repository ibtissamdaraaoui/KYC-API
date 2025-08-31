import logging
import sys
from pathlib import Path

def setup_logging(service_name: str):
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / "logs" / service_name
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{service_name}.log"

    # --- MODIFICATION DU FORMATEUR ---
    # On ajoute le nom du service (logger name) au format.
    formatter = logging.Formatter(
        f'%(asctime)s - [%(levelname)s] - [{service_name}] - %(message)s'
    )

    # --- On récupère le logger racine ---
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers = [] # On vide les handlers pour éviter les doublons

    # --- Création des "destinations" (Handlers) avec le nouveau formateur ---
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    
    # On attache les handlers au logger racine
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # --- On dit aux loggers de Uvicorn d'utiliser nos handlers ---
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = []
    uvicorn_access_logger.addHandler(file_handler)
    uvicorn_access_logger.addHandler(stream_handler)
    uvicorn_access_logger.propagate = False

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = []
    uvicorn_error_logger.addHandler(file_handler)
    uvicorn_error_logger.addHandler(stream_handler)
    uvicorn_error_logger.propagate = False
    
    # --- On calme le logger de Kafka ---
    logging.getLogger("kafka").setLevel(logging.WARNING)

    logging.info("Logging configuré et unifié.")