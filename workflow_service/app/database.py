# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/kyc_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def init_db():
    # Cet import est local pour s'assurer qu'il ne s'exécute que lorsque c'est demandé.
    from app.models import KycCase # On importe UNIQUEMENT le modèle que ce service possède
    Base.metadata.create_all(bind=engine, tables=[KycCase.__table__])
    print("Table 'kyc_cases' initialisée par le workflow_service.")