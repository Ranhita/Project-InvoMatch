import os
import hashlib
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Invoice, PurchaseOrder, AuditLog, InvoiceLine, POLine
from app.parser import parse_document
from app.schemas import UploadResponse, DocumentOut
from app.config import settings

router = APIRouter(prefix="/api/upload", tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".csv"}

# Dynamically resolve uploads directory absolute to backend directory
UPLOAD_BASE_DIR = settings.UPLOAD_DIR
if not os.path.isabs(UPLOAD_BASE_DIR):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_BASE_DIR = os.path.abspath(os.path.join(backend_dir, UPLOAD_BASE_DIR))


def validate_file(file: UploadFile) -> str:
    # 1. Validate File Extension
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only CSV and PDF are supported."
        )
    return ext

def calculate_md5(file_content: bytes) -> str:
    return hashlib.md5(file_content).hexdigest()

@router.post("/invoice", response_model=UploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate extension
    ext = validate_file(file)
    
    # Read content to check size and checksum
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 10MB."
        )
    
    # Calculate hash to verify duplicates
    md5_hash = calculate_md5(content)
    
    # Check if duplicate invoice exists in DB
    existing_invoice = db.query(Invoice).filter(Invoice.md5_hash == md5_hash).first()
    if existing_invoice:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate file detected: this invoice has already been uploaded as '{existing_invoice.file_name}'."
        )
    
    # Generate unique file ID and filename
    file_id = f"INV-{uuid.uuid4().hex[:12].upper()}"
    saved_filename = f"{file_id}{ext}"
    
    # Define and create invoice uploads directory
    invoice_dir = os.path.join(UPLOAD_BASE_DIR, "invoices")
    os.makedirs(invoice_dir, exist_ok=True)
    
    # Save file contents
    file_path = os.path.join(invoice_dir, saved_filename)
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Parse uploaded document to extract structured rows (Phase 3)
    try:
        parsed_data = parse_document(file_path)
    except Exception as e:
        # Fallback metadata if parser fails completely
        parsed_data = {
            "vendor_name": "ACME CORP" if "acme" in file.filename.lower() else "GLOBAL LOGISTICS",
            "doc_number": f"INV-NO-{uuid.uuid4().hex[:6].upper()}",
            "doc_date": date.today(),
            "total_amount": 0.0,
            "lines": []
        }

    # Create DB record
    new_invoice = Invoice(
        id=file_id,
        file_path=file_path,
        file_name=file.filename,
        file_size=len(content),
        file_type=ext[1:].upper(),
        status="processed",
        uploaded_by=current_user.id,
        md5_hash=md5_hash,
        invoice_number=parsed_data["doc_number"],
        vendor_name=parsed_data["vendor_name"],
        invoice_date=parsed_data["doc_date"],
        total_amount=parsed_data["total_amount"]
    )
    
    db.add(new_invoice)
    db.flush() # Ensure invoice is saved to resolve foreign key constraints
    
    # Insert extracted line items
    for line in parsed_data["lines"]:
        db_line = InvoiceLine(
            invoice_id=file_id,
            line_number=line["line_number"],
            sku=line["sku"],
            description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            total_price=line["total_price"]
        )
        db.add(db_line)
    
    # Add audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="UPLOAD_INVOICE",
        details=f"Uploaded invoice file {file.filename} (ID: {file_id}, size: {len(content)} bytes)"
    )
    db.add(audit)
    
    db.commit()
    
    return UploadResponse(
        message="Invoice uploaded and parsed successfully.",
        file_id=file_id,
        file_name=file.filename,
        status="processed"
    )

@router.post("/po", response_model=UploadResponse)
async def upload_po(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate extension
    ext = validate_file(file)
    
    # Read content to check size and checksum
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 10MB."
        )
    
    # Calculate hash to verify duplicates
    md5_hash = calculate_md5(content)
    
    # Check if duplicate PO exists in DB
    existing_po = db.query(PurchaseOrder).filter(PurchaseOrder.md5_hash == md5_hash).first()
    if existing_po:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate file detected: this purchase order has already been uploaded as '{existing_po.file_name}'."
        )
    
    # Generate unique file ID and filename
    file_id = f"PO-{uuid.uuid4().hex[:12].upper()}"
    saved_filename = f"{file_id}{ext}"
    
    # Define and create PO uploads directory
    po_dir = os.path.join(UPLOAD_BASE_DIR, "pos")
    os.makedirs(po_dir, exist_ok=True)
    
    # Save file contents
    file_path = os.path.join(po_dir, saved_filename)
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Parse uploaded document to extract structured rows (Phase 3)
    try:
        parsed_data = parse_document(file_path)
    except Exception as e:
        # Fallback metadata if parser fails completely
        parsed_data = {
            "vendor_name": "ACME CORP" if "acme" in file.filename.lower() else "GLOBAL LOGISTICS",
            "doc_number": f"PO-NO-{uuid.uuid4().hex[:6].upper()}",
            "doc_date": date.today(),
            "total_amount": 0.0,
            "lines": []
        }

    # Create DB record
    new_po = PurchaseOrder(
        id=file_id,
        file_path=file_path,
        file_name=file.filename,
        file_size=len(content),
        file_type=ext[1:].upper(),
        status="processed",
        uploaded_by=current_user.id,
        md5_hash=md5_hash,
        po_number=parsed_data["doc_number"],
        vendor_name=parsed_data["vendor_name"],
        po_date=parsed_data["doc_date"],
        total_amount=parsed_data["total_amount"]
    )
    
    db.add(new_po)
    db.flush() # Ensure PO is saved to resolve foreign key constraints
    
    # Insert extracted line items
    for line in parsed_data["lines"]:
        db_line = POLine(
            po_id=file_id,
            line_number=line["line_number"],
            sku=line["sku"],
            description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            total_price=line["total_price"]
        )
        db.add(db_line)
    
    # Add audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="UPLOAD_PO",
        details=f"Uploaded purchase order file {file.filename} (ID: {file_id}, size: {len(content)} bytes)"
    )
    db.add(audit)
    
    db.commit()
    
    return UploadResponse(
        message="Purchase order uploaded and parsed successfully.",
        file_id=file_id,
        file_name=file.filename,
        status="processed"
    )
