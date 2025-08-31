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

# La logique pour créer la table est ok, elle dépend de l'import de 'models'
from app import models
Base.metadata.create_all(bind=engine)
logging.info("Tables du verification_service initialisées.")