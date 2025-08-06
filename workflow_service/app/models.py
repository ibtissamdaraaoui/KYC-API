import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.sql import func
from app.database import Base 

class KycCaseStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    MATCHED = "MATCHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class KycCase(Base):
    __tablename__ = "kyc_cases"

    id = Column(Integer, primary_key=True, index=True)
    
    # L'ID de corrélation que vous utilisez partout
    kyc_case_id = Column(String, unique=True, index=True, nullable=False)

    # MODIFICATION: Ajout du statut et de la raison de l'échec
    status = Column(SQLAlchemyEnum(KycCaseStatus), nullable=False, default=KycCaseStatus.IN_PROGRESS)
    failure_reason = Column(String, nullable=True) # Pour stocker "DISCORDANCE_RECTO_MRZ", etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())