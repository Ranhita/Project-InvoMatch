import sys
import os

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.append(backend_path)

print("Starting backend configuration verification...")

try:
    from app.config import settings
    print("SUCCESS: Config loaded successfully.")
    print(f"  Database URL: {settings.DATABASE_URL}")
    print(f"  Upload Directory: {settings.UPLOAD_DIR}")
except Exception as e:
    print(f"ERROR: Failed to load settings: {e}")
    sys.exit(1)

try:
    from app.database import engine, Base
    print("SUCCESS: Database engine initialized.")
except Exception as e:
    print(f"ERROR: Failed to initialize database: {e}")
    sys.exit(1)

try:
    from app.models import User, Invoice, PurchaseOrder, Match, Flag, AuditLog
    print("SUCCESS: SQLAlchemy models imported successfully.")
except Exception as e:
    print(f"ERROR: Failed to import models: {e}")
    sys.exit(1)

try:
    from app.schemas import UserCreate, Token, DocumentOut, UploadResponse
    print("SUCCESS: Pydantic schemas compiled successfully.")
except Exception as e:
    print(f"ERROR: Failed to compile Pydantic schemas: {e}")
    sys.exit(1)

try:
    from app.main import app
    print("SUCCESS: FastAPI app instance initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize FastAPI main app: {e}")
    sys.exit(1)

print("\nAll backend components successfully compiled and validated! Ready for launch.")
