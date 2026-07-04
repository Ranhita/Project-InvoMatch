from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional, List

# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Optional[str] = "finance"

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None

# Invoice/PO common output schema
class DocumentOut(BaseModel):
    id: str
    file_name: str
    file_size: int
    file_type: str
    status: str
    uploaded_at: datetime
    uploaded_by: Optional[int] = None
    md5_hash: str
    
    # Metadata fields
    doc_number: Optional[str] = None
    vendor_name: Optional[str] = None
    doc_date: Optional[date] = None
    total_amount: Optional[float] = None
    document_type: str # 'invoice' or 'po'

    class Config:
        from_attributes = True

# Upload Success Response
class UploadResponse(BaseModel):
    message: str
    file_id: str
    file_name: str
    status: str
