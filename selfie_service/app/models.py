# Fichier: selfie_service/app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Modèle miroir pour la relation
class KycCase(Base):
    __tablename__ = "kyc_cases"
    __table_args__ = {'extend_existing': True}
    kyc_case_id = Column(String, primary_key=True)

# Modèle principal du service
class Selfie(Base):
    __tablename__ = "selfies"
    id = Column(Integer, primary_key=True, index=True)
    kyc_case_id = Column(String, ForeignKey("kyc_cases.kyc_case_id"), nullable=False)
    file_key = Column(String, nullable=False)
    encryption_key_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    kyc_case = relationship("KycCase")