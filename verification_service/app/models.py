# Fichier: verification_service/app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base 

# Modèles miroirs pour les relations
class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    vault_key_path = Column(String)

# Modèle principal du service
class VerificationResult(Base):
    __tablename__ = "verification_results"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    status = Column(String, nullable=False)
    raw_text = Column(Text)
    structured_data = Column(JSON) # Utiliser JSON est plus propre que Text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    document = relationship("Document")