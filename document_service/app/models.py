from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base  # <- OK maintenant car Base est défini proprement

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    kyc_case_id = Column(String, nullable=False)    
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    vault_key_path = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
