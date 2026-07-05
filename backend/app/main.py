from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os

from app.database import engine, Base, get_db
from app.config import settings
from app.models import User, Invoice, PurchaseOrder, AuditLog, Match, Flag
from app.schemas import UserCreate, UserOut, Token, DocumentOut, UserLogin
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.upload import router as upload_router
from app.features import get_document_similarities
from app.matcher import reconcile_invoice
from app.reports import generate_csv_report, generate_html_report
from fastapi.responses import StreamingResponse, HTMLResponse
import io

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InvoMatch API",
    description="AI-Assisted Invoice Reconciliation Engine",
    version="1.0.0"
)

from logging.handlers import RotatingFileHandler
import logging

@app.on_event("startup")
def configure_logging():
    os.makedirs("../logs", exist_ok=True)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = "../logs/invomatch.log"
    
    # 5MB log rotations
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    logging.info("Production rotating file logger initialized successfully.")

# Enable CORS for React dev server on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Upload Router
app.include_router(upload_router)

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Try simple select query to verify DB connection
        db.execute(Base.metadata.tables["users"].select().limit(1))
        return {
            "status": "healthy",
            "database": "connected",
            "db_url": settings.DATABASE_URL.split("://")[0] + "://..."  # hide secrets
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}"
        )

@app.post("/api/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    # Create user
    hashed = hash_password(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed,
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log action
    audit = AuditLog(
        user_id=new_user.id,
        action="REGISTER",
        details=f"User {new_user.username} registered with role {new_user.role}"
    )
    db.add(audit)
    db.commit()

    return new_user

# Support both OAuth2 Form login (for Swagger) and raw JSON login (for Axios/Fetch)
@app.post("/api/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    username = None
    password = None

    # Check Content-Type to parse json or form parameters
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password."
        )

    # Fetch user by username or email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    token_data = {"sub": user.username, "user_id": user.id, "role": user.role}
    access_token = create_access_token(data=token_data)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN",
        details=f"User {user.username} logged in successfully."
    )
    db.add(audit)
    db.commit()

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/recent-uploads", response_model=List[DocumentOut])
def get_recent_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch recent invoices and POs for the logged in user
    invoices = db.query(Invoice).filter(Invoice.uploaded_by == current_user.id).order_by(Invoice.uploaded_at.desc()).limit(10).all()
    pos = db.query(PurchaseOrder).filter(PurchaseOrder.uploaded_by == current_user.id).order_by(PurchaseOrder.uploaded_at.desc()).limit(10).all()

    documents = []
    
    for inv in invoices:
        documents.append(DocumentOut(
            id=inv.id,
            file_name=inv.file_name,
            file_size=inv.file_size,
            file_type=inv.file_type,
            status=inv.status,
            uploaded_at=inv.uploaded_at,
            uploaded_by=inv.uploaded_by,
            md5_hash=inv.md5_hash,
            doc_number=inv.invoice_number,
            vendor_name=inv.vendor_name,
            doc_date=inv.invoice_date,
            total_amount=inv.total_amount,
            document_type="invoice"
        ))

    for po in pos:
        documents.append(DocumentOut(
            id=po.id,
            file_name=po.file_name,
            file_size=po.file_size,
            file_type=po.file_type,
            status=po.status,
            uploaded_at=po.uploaded_at,
            uploaded_by=po.uploaded_by,
            md5_hash=po.md5_hash,
            doc_number=po.po_number,
            vendor_name=po.vendor_name,
            doc_date=po.po_date,
            total_amount=po.total_amount,
            document_type="po"
        ))

    # Sort all documents by uploaded_at descending
    documents.sort(key=lambda x: x.uploaded_at, reverse=True)
    return documents[:15]

@app.get("/api/documents/{id}/lines")
def get_document_lines(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if id.startswith("INV-"):
        doc = db.query(Invoice).filter(Invoice.id == id, Invoice.uploaded_by == current_user.id).first()
    elif id.startswith("PO-"):
        doc = db.query(PurchaseOrder).filter(PurchaseOrder.id == id, PurchaseOrder.uploaded_by == current_user.id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
        
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    lines = []
    for line in doc.lines:
        lines.append({
            "id": line.id,
            "line_number": line.line_number,
            "sku": line.sku,
            "description": line.description,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "total_price": line.total_price
        })
    return lines

@app.get("/api/documents/{id}/features")
def get_document_features(
    id: str,
    candidate_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Compute similarity feature vectors (Phase 4)
    if id.startswith("INV-"):
        invoice_id = id
        inv_check = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.uploaded_by == current_user.id).first()
        if not inv_check:
            raise HTTPException(status_code=404, detail="Invoice not found.")
            
        if candidate_id:
            if not candidate_id.startswith("PO-"):
                raise HTTPException(status_code=400, detail="Candidate ID must be a Purchase Order for Invoice comparisons.")
            po_id = candidate_id
            po_check = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id, PurchaseOrder.uploaded_by == current_user.id).first()
            if not po_check:
                raise HTTPException(status_code=404, detail="Purchase Order not found.")
            return get_document_similarities(db, invoice_id, po_id)
        else:
            pos = db.query(PurchaseOrder).filter(PurchaseOrder.uploaded_by == current_user.id).all()
            all_similarities = []
            for po in pos:
                similarities = get_document_similarities(db, invoice_id, po.id)
                if similarities:
                    all_similarities.extend(similarities)
            return all_similarities
            
    elif id.startswith("PO-"):
        po_id = id
        po_check = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id, PurchaseOrder.uploaded_by == current_user.id).first()
        if not po_check:
            raise HTTPException(status_code=404, detail="Purchase Order not found.")
            
        if candidate_id:
            if not candidate_id.startswith("INV-"):
                raise HTTPException(status_code=400, detail="Candidate ID must be an Invoice for PO comparisons.")
            invoice_id = candidate_id
            inv_check = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.uploaded_by == current_user.id).first()
            if not inv_check:
                raise HTTPException(status_code=404, detail="Invoice not found.")
            return get_document_similarities(db, invoice_id, po_id)
        else:
            invoices = db.query(Invoice).filter(Invoice.uploaded_by == current_user.id).all()
            all_similarities = []
            for inv in invoices:
                similarities = get_document_similarities(db, inv.id, po_id)
                if similarities:
                    all_similarities.extend(similarities)
            return all_similarities
    else:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")

@app.post("/api/reconcile/{invoice_id}")
def reconcile_document(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if invoice_id.startswith("PO-"):
            po = db.query(PurchaseOrder).filter(PurchaseOrder.id == invoice_id, PurchaseOrder.uploaded_by == current_user.id).first()
            if not po:
                raise HTTPException(status_code=404, detail=f"PO {invoice_id} not found.")
            
            # Find invoices of the same vendor that are processed and owned by the user
            invoices = db.query(Invoice).filter(Invoice.vendor_name == po.vendor_name, Invoice.uploaded_by == current_user.id).all()
            if not invoices:
                # Fallback to all processed invoices owned by the user
                invoices = db.query(Invoice).filter(Invoice.status == "processed", Invoice.uploaded_by == current_user.id).all()
            
            reconciled_count = 0
            for inv in invoices:
                try:
                    reconcile_invoice(db, inv.id)
                    reconciled_count += 1
                except Exception:
                    pass
            return {"status": "success", "message": f"PO matched against {reconciled_count} invoices."}
        else:
            # Check ownership of invoice
            inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.uploaded_by == current_user.id).first()
            if not inv:
                raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found.")
            result = reconcile_invoice(db, invoice_id)
            return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation error: {str(e)}")

@app.get("/api/matches")
def get_matches_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    matches = db.query(Match).join(Invoice, Match.invoice_id == Invoice.id).filter(Invoice.uploaded_by == current_user.id).order_by(Match.created_at.desc()).all()
    results = []
    
    for match in matches:
        inv = db.query(Invoice).filter(Invoice.id == match.invoice_id, Invoice.uploaded_by == current_user.id).first()
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == match.po_id, PurchaseOrder.uploaded_by == current_user.id).first()
        flags_count = db.query(Flag).filter(Flag.invoice_id == match.invoice_id).count()
        
        results.append({
            "id": match.id,
            "invoice_id": match.invoice_id,
            "invoice_number": inv.invoice_number if inv else "N/A",
            "invoice_file_name": inv.file_name if inv else "N/A",
            "invoice_amount": inv.total_amount if inv else 0.0,
            "po_id": match.po_id,
            "po_number": po.po_number if po else "N/A",
            "po_file_name": po.file_name if po else "N/A",
            "po_amount": po.total_amount if po else 0.0,
            "vendor_name": inv.vendor_name if inv else (po.vendor_name if po else "N/A"),
            "match_score": match.match_score,
            "risk_score": match.risk_score,
            "status": match.status,
            "created_at": match.created_at,
            "flags_count": flags_count
        })
    return results

class MatchDecision(BaseModel):
    comment: Optional[str] = None

@app.post("/api/matches/{id}/approve")
def approve_reconciliation_match(
    id: int,
    body: Optional[MatchDecision] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    match = db.query(Match).join(Invoice, Match.invoice_id == Invoice.id).filter(Match.id == id, Invoice.uploaded_by == current_user.id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    comment_text = body.comment if body else None
    
    match.status = "approved"
    if comment_text:
        match.comment = comment_text
    
    # Update documents statuses to approved
    inv = db.query(Invoice).filter(Invoice.id == match.invoice_id, Invoice.uploaded_by == current_user.id).first()
    if inv:
        inv.status = "approved"
        
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == match.po_id, PurchaseOrder.uploaded_by == current_user.id).first()
    if po:
        po.status = "approved"
        
    # Resolve all flags
    db.query(Flag).filter(Flag.invoice_id == match.invoice_id).update({"is_resolved": True})
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="APPROVE_MATCH",
        details=f"Manually approved match (ID: {id}) linking Invoice {match.invoice_id} with PO {match.po_id}. Comment: {comment_text or 'None'}"
    )
    db.add(audit)
    db.commit()
    
    return {"status": "approved", "message": "Match successfully approved."}

@app.post("/api/matches/{id}/reject")
def reject_reconciliation_match(
    id: int,
    body: Optional[MatchDecision] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    match = db.query(Match).filter(Match.id == id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    comment_text = body.comment if body else None
    
    match.status = "rejected"
    if comment_text:
        match.comment = comment_text
    
    inv = db.query(Invoice).filter(Invoice.id == match.invoice_id).first()
    if inv:
        inv.status = "processed"
        
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == match.po_id).first()
    if po:
        po.status = "processed"
        
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="REJECT_MATCH",
        details=f"Manually rejected match (ID: {id}) linking Invoice {match.invoice_id} with PO {match.po_id}. Comment: {comment_text or 'None'}"
    )
    db.add(audit)
    db.commit()
    
    return {"status": "rejected", "message": "Match successfully rejected."}

@app.post("/api/matches/{id}/needs-review")
def mark_match_needs_review(
    id: int,
    body: MatchDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    match = db.query(Match).filter(Match.id == id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    match.status = "needs_review"
    match.comment = body.comment
    
    inv = db.query(Invoice).filter(Invoice.id == match.invoice_id).first()
    if inv:
        inv.status = "anomaly"
        
    # Add flag for manual review
    flag = Flag(
        invoice_id=match.invoice_id,
        flag_type="needs_review",
        severity="medium",
        description=f"Marked as Needs Review by user: {body.comment}",
        explained_by_ai="User requested additional human review on this match proposal."
    )
    db.add(flag)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="NEEDS_REVIEW_MATCH",
        details=f"Marked match (ID: {id}) as Needs Review. Comment: {body.comment}"
    )
    db.add(audit)
    db.commit()
    
    return {"status": "needs_review", "message": "Match successfully flagged for manual review."}

@app.get("/api/documents/{id}/flags")
def get_document_flags(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify invoice ownership
    inv = db.query(Invoice).filter(Invoice.id == id, Invoice.uploaded_by == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    flags = db.query(Flag).filter(Flag.invoice_id == id).all()
    results = []
    for f in flags:
        results.append({
            "id": f.id,
            "flag_type": f.flag_type,
            "severity": f.severity,
            "description": f.description,
            "explained_by_ai": f.explained_by_ai,
            "is_resolved": f.is_resolved,
            "created_at": f.created_at
        })
    return results

@app.get("/api/documents/{id}/download")
def download_document(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Invoice).filter(Invoice.id == id, Invoice.uploaded_by == current_user.id).first()
    if not doc:
        doc = db.query(PurchaseOrder).filter(PurchaseOrder.id == id, PurchaseOrder.uploaded_by == current_user.id).first()
        
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Original document file not found on disk.")
        
    # Log the download action
    audit = AuditLog(
        user_id=current_user.id,
        action="DOWNLOAD_DOCUMENT",
        details=f"Downloaded original document: {doc.file_name} (ID: {id})"
    )
    db.add(audit)
    db.commit()
    
    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type="application/pdf" if doc.file_name.lower().endswith(".pdf") else "text/csv"
    )

@app.get("/api/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logs = db.query(AuditLog).filter(AuditLog.user_id == current_user.id).order_by(AuditLog.created_at.desc()).all()
    results = []
    for log in logs:
        user_obj = db.query(User).filter(User.id == log.user_id).first()
        results.append({
            "id": log.id,
            "username": user_obj.username if user_obj else "System",
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at
        })
    return results

@app.get("/api/analytics")
def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_invoices = db.query(Invoice).filter(Invoice.uploaded_by == current_user.id).count()
    total_pos = db.query(PurchaseOrder).filter(PurchaseOrder.uploaded_by == current_user.id).count()
    
    matches = db.query(Match).join(Invoice, Match.invoice_id == Invoice.id).filter(Invoice.uploaded_by == current_user.id).all()
    
    matched_count = len([m for m in matches if m.status in ["approved", "matched"]])
    pending_count = len([m for m in matches if m.status == "pending"])
    rejected_count = len([m for m in matches if m.status == "rejected"])
    needs_review_count = len([m for m in matches if m.status == "needs_review"])
    
    high_risk_count = len([m for m in matches if m.risk_score >= 61.0])
    
    # Calculate match rate
    match_rate = (matched_count / max(total_invoices, 1)) * 100.0
    
    # Risk distribution
    risk_dist = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for m in matches:
        if m.risk_score >= 81.0:
            risk_dist["Critical"] += 1
        elif m.risk_score >= 61.0:
            risk_dist["High"] += 1
        elif m.risk_score >= 31.0:
            risk_dist["Medium"] += 1
        else:
            risk_dist["Low"] += 1
            
    # Monthly uploads trend (mock grouping by month based on invoices)
    # Since SQLite doesn't guarantee easy date formats across environments,
    # we can construct simple month aggregations programmatically
    monthly_data = {}
    for inv in db.query(Invoice).filter(Invoice.uploaded_by == current_user.id).all():
        m_str = inv.uploaded_at.strftime("%b %Y") if inv.uploaded_at else "Jun 2026"
        monthly_data[m_str] = monthly_data.get(m_str, 0) + 1
        
    monthly_trend = [{"month": k, "count": v} for k, v in monthly_data.items()]
    if not monthly_trend:
        monthly_trend = [{"month": "Jun 2026", "count": 0}]
        
    # Vendor performance metrics (group averages)
    vendor_sums = {}
    for m in matches:
        inv = db.query(Invoice).filter(Invoice.id == m.invoice_id).first()
        vendor = inv.vendor_name if inv else "Unknown Vendor"
        if vendor not in vendor_sums:
            vendor_sums[vendor] = {"scores": [], "count": 0}
        vendor_sums[vendor]["scores"].append(m.match_score)
        vendor_sums[vendor]["count"] += 1
        
    vendor_perf = []
    for vendor, data in vendor_sums.items():
        avg_score = sum(data["scores"]) / len(data["scores"])
        vendor_perf.append({
            "vendor": vendor,
            "average_match_score": float(avg_score * 100.0),
            "invoice_count": data["count"]
        })
    vendor_perf.sort(key=lambda x: x["average_match_score"], reverse=True)
    
    return {
        "summary": {
            "total_invoices": total_invoices,
            "total_pos": total_pos,
            "matched": matched_count,
            "pending": pending_count,
            "rejected": rejected_count,
            "needs_review": needs_review_count,
            "high_risk": high_risk_count,
            "match_rate_percent": float(match_rate)
        },
        "risk_distribution": risk_dist,
        "monthly_trend": monthly_trend,
        "vendor_performance": vendor_perf
    }

@app.get("/api/reports/export")
def export_reports_log(
    report_type: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if report_type not in ["monthly", "vendor", "anomaly", "audit", "finance"]:
        raise HTTPException(status_code=400, detail="Invalid report type.")
        
    # Log report generation audit
    audit = AuditLog(
        user_id=current_user.id,
        action="EXPORT_REPORT",
        details=f"Exported report: {report_type} ({format})"
    )
    db.add(audit)
    db.commit()
    
    if format == "csv":
        csv_data = generate_csv_report(db, report_type)
        return StreamingResponse(
            io.BytesIO(csv_data.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=invomatch_report_{report_type}.csv"}
        )
    elif format == "html":
        html_data = generate_html_report(db, report_type)
        return HTMLResponse(content=html_data, status_code=200)
    else:
        raise HTTPException(status_code=400, detail="Invalid export format (supports 'csv' or 'html').")
