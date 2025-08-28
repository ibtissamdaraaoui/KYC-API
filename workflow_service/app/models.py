# Fichier: workflow_service/app/models.py

import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# --- L'ENUM EST DÉFINI ICI ---
class KycCaseStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    MATCHED = "MATCHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class KycCase(Base):
    __tablename__ = "kyc_cases"
    id = Column(Integer, primary_key=True, index=True)
    kyc_case_id = Column(String, unique=True, index=True, nullable=False)
    
    # La colonne utilise l'Enum défini juste au-dessus
    status = Column(SQLAlchemyEnum(KycCaseStatus), nullable=False, default=KycCaseStatus.IN_PROGRESS)
    
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    documents = relationship("Document")
    selfies = relationship("Selfie")


# --- AJOUTER OU MODIFIER CE MODÈLE ---
class ApiClient(Base):
    __tablename__ = "api_clients"
    
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    application_id = Column(String, unique=True, index=True)
    
    # LIGNE CRUCIALE À AJOUTER :
    jwt_secret = Column(String, nullable=False, unique=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    
# Modèles miroirs (inchangés)
class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    kyc_case_id = Column(String, ForeignKey("kyc_cases.kyc_case_id"))

class Selfie(Base):
    __tablename__ = "selfies"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    kyc_case_id = Column(String, ForeignKey("kyc_cases.kyc_case_id"))