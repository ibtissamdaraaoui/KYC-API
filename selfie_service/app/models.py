from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

from app.database import Base


class Selfie(Base):
    __tablename__ = "selfies"

    id = Column(Integer, primary_key=True, index=True)
    kyc_case_id = Column(String, index=True)
    file_key = Column(String, nullable=False)
    encryption_key_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
