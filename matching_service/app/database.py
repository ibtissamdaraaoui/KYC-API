# Fichier: matching_service/app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Charger les variables d'environnement depuis un fichier .env
load_dotenv()

# Récupérer l'URL de la base de données depuis les variables d'environnement
# avec une valeur par défaut pour le développement local.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kyc_db")

if not DATABASE_URL:
    raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie.")

# Créer le moteur de base de données
engine = create_engine(DATABASE_URL)

# Créer une fabrique de sessions qui sera utilisée pour interagir avec la BDD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Créer une classe de base pour nos modèles déclaratifs SQLAlchemy
Base = declarative_base()

def init_db():
    """
    Crée toutes les tables dans la base de données qui héritent de Base.
    À appeler au démarrage de l'application.
    """
    print("Initialisation de la base de données...")
    Base.metadata.create_all(bind=engine)
    print("Tables créées (si elles n'existaient pas).")