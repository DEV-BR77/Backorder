from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings
s=get_settings()
if s.database_url.startswith("sqlite:///"): Path("data").mkdir(exist_ok=True)
engine=create_engine(s.database_url,connect_args={"check_same_thread":False} if s.database_url.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
class Base(DeclarativeBase): pass
def get_db():
 db=SessionLocal()
 try: yield db
 finally: db.close()
