# Fichier: verification_service/app/crud.py

from sqlalchemy.orm import Session
from . import models, schemas # Importer les modèles et schémas locaux

def create_verification_result(db: Session, result: schemas.VerificationResultCreate) -> models.VerificationResult:
    """
    Insère un nouveau résultat de vérification dans la base de données.
    
    Args:
        db: La session SQLAlchemy.
        result: Un objet Pydantic VerificationResultCreate contenant les données à insérer.

    Returns:
        L'objet SQLAlchemy VerificationResult qui vient d'être créé.
    """
    # Créer une instance du modèle SQLAlchemy en utilisant les données du schéma Pydantic
    # .model_dump() convertit le schéma Pydantic en un dictionnaire compatible
    db_result = models.VerificationResult(**result.model_dump())
    
    # Ajouter, commiter et rafraîchir pour obtenir l'ID généré par la BDD
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    
    return db_result