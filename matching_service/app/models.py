# Fichier: matching_service/app/models.py

from sqlalchemy import Column, String, Boolean, Float, JSON, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base

# =====================================================================
# MODÈLES SPÉCIFIQUES AU matching_service
# =====================================================================

class MatchingTask(Base):
    """Table de suivi des tâches de matching."""
    __tablename__ = "matching_tasks"
    kyc_case_id = Column(String, primary_key=True, index=True)
    document_verified_received = Column(Boolean, default=False, nullable=False)
    selfie_uploaded_received = Column(Boolean, default=False, nullable=False)
    document_id = Column(Integer)
    recto_path = Column(String)
    selfie_id = Column(Integer)
    selfie_path = Column(String)

class MatchingResult(Base):
    """Table pour stocker le résultat final du matching."""
    __tablename__ = "matching_results"
    id = Column(Integer, primary_key=True, index=True)
    kyc_case_id = Column(String, index=True, nullable=False)
    is_match = Column(Boolean)
    distance = Column(Float)
    model_name = Column(String)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =====================================================================
# MODÈLES "MIROIR" MINIMALISTES DES AUTRES SERVICES
# =====================================================================

class Document(Base):
    """
    Modèle miroir MINIMAL de la table 'documents'.
    Ne contient que les champs nécessaires à ce service.
    """
    __tablename__ = "documents"
    # Cet argument est une bonne pratique pour éviter les erreurs de redéclaration
    # quand plusieurs modèles font référence à la même table.
    __table_args__ = {'extend_existing': True} 

    id = Column(Integer, primary_key=True)
    # Le seul autre champ dont nous avons besoin est celui contenant le chemin Vault.
    vault_key_path = Column(String, nullable=False)


class Selfie(Base):
    """
    Modèle miroir MINIMAL de la table 'selfies'.
    """
    __tablename__ = "selfies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    # Le seul autre champ dont nous avons besoin est celui contenant le chemin Vault.
    encryption_key_id = Column(String, nullable=False)