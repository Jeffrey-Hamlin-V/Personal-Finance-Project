"""
API Schemas - Pydantic models for request/response validation
Demonstrates: Type safety, validation, API contracts
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


# ==================
# USER SCHEMAS
# ==================

class UserCreate(BaseModel):
    """Schema for user registration"""
    user_id: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login"""
    user_id: str
    password: str


class UserResponse(BaseModel):
    """Schema for user data in responses"""
    user_id: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str


# ==================
# TRANSACTION SCHEMAS
# ==================

class TransactionBase(BaseModel):
    """Base transaction schema"""
    transaction_id: str
    transaction_date: datetime
    amount: float
    currency: str = "EUR"
    merchant: str
    category: str
    timestamp: datetime
    payment_method: Optional[str] = None
    is_credit: bool = False


class TransactionResponse(TransactionBase):
    """Extended transaction response with ML predictions"""
    id: int
    user_id: str
    upload_id: Optional[str] = None
    
    # ML predictions
    predicted_category: Optional[str] = None
    prediction_confidence: Optional[float] = None
    
    # Anomaly flags
    is_amount_anomaly: bool = False
    is_frequency_anomaly: bool = False
    is_merchant_anomaly: bool = False
    anomaly_score: Optional[float] = None
    
    # Time features
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    is_weekend: bool = False
    is_night: bool = False
    
    class Config:
        from_attributes = True


class TransactionList(BaseModel):
    """Paginated transaction list"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int


# ==================
# UPLOAD SCHEMAS
# ==================

class UploadResponse(BaseModel):
    """Upload status response"""
    upload_id: str
    user_id: str
    filename: str
    upload_date: datetime
    num_transactions: int
    status: str  # pending, processing, completed, failed
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class UploadStatusResponse(BaseModel):
    """Detailed upload status with progress"""
    upload_id: str
    status: str
    num_transactions: int
    categorization_completed: bool
    anomaly_detection_completed: bool
    progress_pct: float
    error_message: Optional[str] = None


# ==================
# INSIGHT SCHEMAS
# ==================

class InsightResponse(BaseModel):
    """Single insight"""
    type: str  # spending_summary, anomaly_alert, trend, top_merchant
    title: str
    description: str
    category: Optional[str] = None
    amount: Optional[float] = None
    severity: Optional[str] = None  # high, medium, low


class SpendingSummary(BaseModel):
    """Overall spending summary"""
    total_income: float
    total_spending: float
    net: float
    num_transactions: int
    category_breakdown: Dict[str, float]
    avg_transaction: float


class DashboardResponse(BaseModel):
    """Complete dashboard data"""
    summary: SpendingSummary
    insights: List[InsightResponse]
    recent_transactions: List[TransactionResponse]
    anomaly_count: int


# ==================
# ANALYTICS SCHEMAS
# ==================

class CategorySpending(BaseModel):
    """Spending by category"""
    category: str
    total: float
    count: int
    avg: float
    pct_of_total: float


class MerchantSpending(BaseModel):
    """Spending by merchant"""
    merchant: str
    total: float
    count: int
    category: str


class AnalyticsResponse(BaseModel):
    """Analytics aggregations"""
    by_category: List[CategorySpending]
    by_merchant: List[MerchantSpending]
    total_spent: float
    total_income: float


# ==================
# JOB SCHEMAS
# ==================

class JobStatus(BaseModel):
    """Background job status"""
    job_id: str
    job_type: str
    status: str  # pending, running, completed, failed
    progress_pct: float
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ==================
# ERROR SCHEMAS
# ==================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    status_code: int