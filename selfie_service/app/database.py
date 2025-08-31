# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

# Lire la variable d'environnement chargée par le point d'entrée de l'application
DATABASE_URL = os.getenv("DATABASE_URL")

# Vérification pour s'assurer que la variable est bien chargée
if not DATABASE_URL:
    raise ValueError("ERREUR: La variable d'environnement DATABASE_URL n'est pas définie.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def init_db():
    from app.models import Selfie
    Base.metadata.create_all(bind=engine, tables=[Selfie.__table__])
    logging.info("Table 'selfies' initialisée par le selfie_service.")