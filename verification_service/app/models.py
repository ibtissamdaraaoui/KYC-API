from sqlalchemy import Column, Integer, String , ForeignKey ,Text ,DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.database import Base 


class Document(Base):
    __tablename__ = "documents"  # Assure-toi que le nom correspond à celui dans la base

    id = Column(Integer, primary_key=True, index=True)
    vault_key_path = Column(String, nullable=False)

    
class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)

    # Référence au cas KYC
    kyc_case_id = Column(String, index=True, nullable=False)
    # Clé étrangère vers le document stocké
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    structured_data = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
