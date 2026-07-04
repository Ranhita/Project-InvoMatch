import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Dynamically resolve SQLite database URL relative to backend directory to ensure consistency
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_relative_path = db_url.replace("sqlite:///", "")
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    absolute_db_path = os.path.abspath(os.path.join(backend_dir, db_relative_path))
    
    # Ensure database folder exists
    db_dir = os.path.dirname(absolute_db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    db_url = f"sqlite:///{absolute_db_path}"

# Create engine
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
