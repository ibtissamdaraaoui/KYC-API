# Fichier: matching_service/app/models.py
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# --- MODÈLES MIROIRS NÉCESSAIRES ---
class KycCase(Base):
    __tablename__ = "kyc_cases"
    __table_args__ = {'extend_existing': True}
    kyc_case_id = Column(String, primary_key=True)

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True} 
    id = Column(Integer, primary_key=True)
    recto_path = Column(String, nullable=False)
    vault_key_path = Column(String, nullable=False)

class Selfie(Base):
    __tablename__ = "selfies"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    file_key = Column(String, nullable=False)
    encryption_key_id = Column(String, nullable=False)

# --- MODÈLES PRINCIPAUX DU SERVICE ---
class MatchingTask(Base):
    __tablename__ = "matching_tasks"
    kyc_case_id = Column(String, ForeignKey("kyc_cases.kyc_case_id"), primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    selfie_id = Column(Integer, ForeignKey("selfies.id"), nullable=True)
    status = Column(String, default="PENDING", nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class MatchingResult(Base):
    __tablename__ = "matching_results"
    id = Column(Integer, primary_key=True, index=True)
    kyc_case_id = Column(String, ForeignKey("kyc_cases.kyc_case_id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    selfie_id = Column(Integer, ForeignKey("selfies.id"), nullable=False)
    match_result = Column(String, nullable=False)
    distance = Column(Float)
    model_details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())