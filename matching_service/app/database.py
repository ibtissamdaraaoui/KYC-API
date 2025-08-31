# Fichier: matching_service/app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging



# Lire la variable d'environnement chargée par le point d'entrée de l'application
DATABASE_URL = os.getenv("DATABASE_URL")

# Vérification pour s'assurer que la variable est bien chargée
if not DATABASE_URL:
    raise ValueError("ERREUR: La variable d'environnement DATABASE_URL n'est pas définie.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from app.models import MatchingTask, MatchingResult
    tables_to_create = [MatchingTask.__table__, MatchingResult.__table__]
    Base.metadata.create_all(bind=engine, tables=tables_to_create)
    logging.info("Tables 'matching_tasks' et 'matching_results' initialisées par le matching_service.")