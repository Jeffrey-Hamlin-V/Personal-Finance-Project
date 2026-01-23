"""
Database Models - SQLAlchemy ORM
Matches cleaned transaction CSV schema
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User table - supports multi-user system"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    uploads = relationship("Upload", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, email={self.email})>"


class Upload(Base):
    """Upload table - represents one CSV file upload (typically one month)"""
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Upload metadata
    filename = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, index=True)
    num_transactions = Column(Integer, default=0)
    
    # Processing status
    status = Column(String(50), default='pending', index=True)  # pending, processing, completed, failed
    error_message = Column(String(1000), nullable=True)
    
    # ML processing results
    categorization_completed = Column(Boolean, default=False)
    anomaly_detection_completed = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="uploads")
    transactions = relationship("Transaction", back_populates="upload", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Upload(id={self.upload_id}, status={self.status})>"


class Transaction(Base):
    """Transaction table - matches cleaned CSV schema"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    upload_id = Column(String(100), ForeignKey("uploads.upload_id"), nullable=True, index=True)
    
    # Transaction details (from CSV)
    transaction_date = Column(DateTime, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)  # Full timestamp with time
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="EUR")
    payment_method = Column(String(50), nullable=True)
    is_credit = Column(Boolean, default=False)
    
    # Merchant & description
    merchant = Column(String(255), nullable=False, index=True)
    clean_description = Column(String(1000), nullable=False)  # Cleaned text for ML
    
    # Category (ground truth from CSV)
    category = Column(String(100), nullable=False, index=True)
    
    # ML predictions (populated by inference pipeline)
    predicted_category = Column(String(100), nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    
    # Time features (from CSV)
    hour_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    is_weekend = Column(Boolean, default=False)
    is_night = Column(Boolean, default=False)
    
    # Anomaly flags (from CSV + ML detection)
    is_amount_anomaly = Column(Boolean, default=False, index=True)
    is_frequency_anomaly = Column(Boolean, default=False)
    is_merchant_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)  # Overall anomaly score from ML
    
    # Processing metadata
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    upload = relationship("Upload", back_populates="transactions")
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_user_date', 'user_id', 'transaction_date'),
        Index('ix_user_category', 'user_id', 'category'),
        Index('ix_user_anomaly', 'user_id', 'is_amount_anomaly'),
        Index('ix_upload_date', 'upload_id', 'transaction_date'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.transaction_id}, merchant={self.merchant}, amount={self.amount})>"


class Insight(Base):
    """Generated insights table - stores ML analysis results"""
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Time period for insight
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Insight content
    insight_type = Column(String(50), nullable=False)  # 'spending_summary', 'anomaly_alert', 'trend'
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    
    # Supporting data
    category = Column(String(100), nullable=True)
    amount_change = Column(Float, nullable=True)
    percent_change = Column(Float, nullable=True)
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="insights")
    
    __table_args__ = (
        Index('ix_user_period', 'user_id', 'period_start', 'period_end'),
    )
    
    def __repr__(self):
        return f"<Insight(type={self.insight_type}, title={self.title})>"


class MLModel(Base):
    """Model versioning table - tracks deployed models"""
    __tablename__ = "ml_models"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)  # 'categorizer', 'anomaly_detector'
    version = Column(String(50), nullable=False)
    
    # Model metadata
    algorithm = Column(String(100), nullable=False)
    accuracy = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    
    # Storage location
    model_path = Column(String(500), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=False)
    deployed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_model_active', 'model_name', 'is_active'),
    )
    
    def __repr__(self):
        return f"<MLModel(name={self.model_name}, version={self.version}, active={self.is_active})>"


class ProcessingJob(Base):
    """Job queue table - tracks async ML processing"""
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    upload_id = Column(String(100), nullable=True, index=True)
    
    # Job details
    job_type = Column(String(50), nullable=False)  # 'categorize', 'detect_anomalies', 'generate_insights'
    status = Column(String(50), nullable=False, default='pending', index=True)  # pending, running, completed, failed
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(String(1000), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.job_id}, type={self.job_type}, status={self.status})>"