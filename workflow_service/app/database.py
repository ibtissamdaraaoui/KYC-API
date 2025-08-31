# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    from app.models import KycCase ,ApiClient
    Base.metadata.create_all(bind=engine, tables=[KycCase.__table__,ApiClient.__table__])
    logging.info("Table 'kyc_cases' initialisée par le workflow_service.")