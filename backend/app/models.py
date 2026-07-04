from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="finance")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="uploader")
    purchase_orders = relationship("PurchaseOrder", back_populates="uploader")
    audit_logs = relationship("AuditLog", back_populates="user")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(100), primary_key=True, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    status = Column(String(50), default="uploaded")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    md5_hash = Column(String(32), unique=True, nullable=False)

    # Extracted Metadata (populated by parser engine in Phase 3)
    invoice_number = Column(String(100), nullable=True)
    vendor_name = Column(String(255), nullable=True)
    invoice_date = Column(Date, nullable=True)
    total_amount = Column(Float, nullable=True)

    # Relationships
    uploader = relationship("User", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="invoice", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="invoice", cascade="all, delete-orphan")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String(100), primary_key=True, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    status = Column(String(50), default="uploaded")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    md5_hash = Column(String(32), unique=True, nullable=False)

    # Extracted Metadata
    po_number = Column(String(100), nullable=True)
    vendor_name = Column(String(255), nullable=True)
    po_date = Column(Date, nullable=True)
    total_amount = Column(Float, nullable=True)

    # Relationships
    uploader = relationship("User", back_populates="purchase_orders")
    lines = relationship("POLine", back_populates="po", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="po", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(100), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    line_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    sku = Column(String(100), nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="lines")


class POLine(Base):
    __tablename__ = "po_lines"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(String(100), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    line_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    sku = Column(String(100), nullable=True)

    # Relationships
    po = relationship("PurchaseOrder", back_populates="lines")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(100), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    po_id = Column(String(100), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Float, nullable=False)
    risk_score = Column(Float, default=0.0)
    matched_by = Column(String(50), nullable=False) # e.g. 'rules', 'ml', 'fuzzy'
    status = Column(String(50), default="pending") # e.g. 'pending', 'approved', 'rejected'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="matches")
    po = relationship("PurchaseOrder", back_populates="matches")


class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(100), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    flag_type = Column(String(50), nullable=False) # 'pricing_anomaly', 'quantity_mismatch', etc.
    severity = Column(String(50), nullable=False) # 'low', 'medium', 'high'
    description = Column(Text, nullable=False)
    explained_by_ai = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="flags")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
