"""
API Routes - FastAPI endpoints
Demonstrates: RESTful design, async processing, proper error handling
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import pandas as pd
import uuid
from datetime import datetime
import logging

from database import get_db, Transaction, Upload, User, Insight
from .schemas import (
    TransactionResponse, TransactionList, UploadResponse,
    DashboardResponse, InsightResponse, SpendingSummary,
    AnalyticsResponse, CategorySpending, MerchantSpending,
    UploadStatusResponse
)
from ml import get_categorizer, get_anomaly_detector, get_insight_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# ==================
# UPLOAD ENDPOINTS
# ==================

@router.post("/upload", response_model=UploadResponse, tags=["Uploads"])
async def upload_transactions(
    file: UploadFile = File(...),
    user_id: str = Query(..., description="User ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload CSV of transactions
    Triggers async ML processing in background
    """
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    # Create user if not exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id, email=f"{user_id}@example.com")
        db.add(user)
        db.commit()
    
    # Read CSV
    try:
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # Validate required columns
        required_cols = ['transaction_id', 'transaction_date', 'amount', 'merchant', 'clean_description']
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing}"
            )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")
    
    # Create upload record
    upload_id = f"upload_{uuid.uuid4().hex[:12]}"
    upload = Upload(
        upload_id=upload_id,
        user_id=user_id,
        filename=file.filename,
        num_transactions=len(df),
        status='processing'
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    # Process in background
    background_tasks.add_task(process_upload, upload_id, df, user_id)
    
    logger.info(f"✅ Upload {upload_id} created with {len(df)} transactions")
    
    return upload


@router.get("/uploads/{upload_id}/status", response_model=UploadStatusResponse, tags=["Uploads"])
def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
    """Get status of an upload"""
    
    upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Calculate progress
    if upload.status == 'completed':
        progress = 100.0
    elif upload.status == 'processing':
        progress = 50.0  # Simplified; could track actual progress
    else:
        progress = 0.0
    
    return UploadStatusResponse(
        upload_id=upload.upload_id,
        status=upload.status,
        num_transactions=upload.num_transactions,
        categorization_completed=upload.categorization_completed,
        anomaly_detection_completed=upload.anomaly_detection_completed,
        progress_pct=progress
    )


# ==================
# TRANSACTION ENDPOINTS
# ==================

@router.get("/transactions", response_model=TransactionList, tags=["Transactions"])
def get_transactions(
    user_id: str = Query(...),
    category: Optional[str] = None,
    is_anomaly: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get transactions with filtering and pagination
    Demonstrates: Query optimization, pagination
    """
    
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    
    # Apply filters
    if category:
        query = query.filter(Transaction.category == category)
    
    if is_anomaly is not None:
        if is_anomaly:
            query = query.filter(Transaction.anomaly_score > 0)
        else:
            query = query.filter(
                (Transaction.anomaly_score == 0) | (Transaction.anomaly_score.is_(None))
            )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    transactions = query.order_by(desc(Transaction.transaction_date))\
                       .offset((page - 1) * page_size)\
                       .limit(page_size)\
                       .all()
    
    return TransactionList(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse, tags=["Transactions"])
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Get single transaction by ID"""
    
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return txn


# ==================
# DASHBOARD & INSIGHTS
# ==================

@router.get("/dashboard", response_model=DashboardResponse, tags=["Dashboard"])
def get_dashboard(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get complete dashboard data
    Demonstrates: Data aggregation, complex queries
    """
    
    # Get all transactions
    transactions = db.query(Transaction)\
                    .filter(Transaction.user_id == user_id)\
                    .all()
    
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for user")
    
    # Convert to dicts for analysis
    txn_dicts = [
        {
            'amount': t.amount,
            'category': t.category,
            'is_credit': t.is_credit,
            'merchant': t.merchant,
            'anomaly_score': t.anomaly_score or 0,
            'is_amount_anomaly': t.is_amount_anomaly,
            'is_frequency_anomaly': t.is_frequency_anomaly,
            'is_merchant_anomaly': t.is_merchant_anomaly,
            'transaction_date': t.transaction_date,
            'is_weekend': t.is_weekend,
            'is_night': t.is_night
        }
        for t in transactions
    ]
    
    # Generate insights
    insight_engine = get_insight_engine()
    insights_data = insight_engine.generate_insights(txn_dicts)
    summary_data = insight_engine.get_spending_summary(txn_dicts)
    
    # Get recent transactions
    recent = db.query(Transaction)\
               .filter(Transaction.user_id == user_id)\
               .order_by(desc(Transaction.transaction_date))\
               .limit(10)\
               .all()
    
    # Count anomalies
    anomaly_count = db.query(Transaction)\
                     .filter(Transaction.user_id == user_id)\
                     .filter(Transaction.anomaly_score > 0)\
                     .count()
    
    return DashboardResponse(
        summary=SpendingSummary(**summary_data),
        insights=[InsightResponse(**i) for i in insights_data],
        recent_transactions=recent,
        anomaly_count=anomaly_count
    )


@router.get("/insights", response_model=List[InsightResponse], tags=["Dashboard"])
def get_insights(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get AI-generated insights"""
    
    transactions = db.query(Transaction)\
                    .filter(Transaction.user_id == user_id)\
                    .all()
    
    if not transactions:
        return []
    
    txn_dicts = [
        {
            'amount': t.amount,
            'category': t.category,
            'is_credit': t.is_credit,
            'merchant': t.merchant,
            'anomaly_score': t.anomaly_score or 0,
            'is_amount_anomaly': t.is_amount_anomaly,
            'is_frequency_anomaly': t.is_frequency_anomaly,
            'is_merchant_anomaly': t.is_merchant_anomaly,
            'transaction_date': t.transaction_date,
            'is_weekend': t.is_weekend,
            'is_night': t.is_night
        }
        for t in transactions
    ]
    
    insight_engine = get_insight_engine()
    insights = insight_engine.generate_insights(txn_dicts)
    
    return [InsightResponse(**i) for i in insights]


# ==================
# ANALYTICS ENDPOINTS
# ==================

@router.get("/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
def get_analytics(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get spending analytics
    Demonstrates: SQL aggregations, data transformations
    """
    
    # Category aggregations
    category_stats = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count'),
        func.avg(Transaction.amount).label('avg')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.is_credit == False
    ).group_by(Transaction.category).all()
    
    total_spent = sum(c.total for c in category_stats)
    
    by_category = [
        CategorySpending(
            category=c.category,
            total=float(c.total),
            count=c.count,
            avg=float(c.avg),
            pct_of_total=float((c.total / total_spent * 100) if total_spent > 0 else 0)
        )
        for c in category_stats
    ]
    
    # Merchant aggregations
    merchant_stats = db.query(
        Transaction.merchant,
        Transaction.category,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.is_credit == False
    ).group_by(Transaction.merchant, Transaction.category)\
     .order_by(desc('total'))\
     .limit(10).all()
    
    by_merchant = [
        MerchantSpending(
            merchant=m.merchant,
            total=float(m.total),
            count=m.count,
            category=m.category
        )
        for m in merchant_stats
    ]
    
    # Total income
    total_income = db.query(func.sum(Transaction.amount))\
                    .filter(Transaction.user_id == user_id, Transaction.is_credit == True)\
                    .scalar() or 0.0
    
    return AnalyticsResponse(
        by_category=by_category,
        by_merchant=by_merchant,
        total_spent=float(total_spent),
        total_income=float(total_income)
    )


# ==================
# BACKGROUND PROCESSING
# ==================

def process_upload(upload_id: str, df: pd.DataFrame, user_id: str):
    """
    Background task to process uploaded transactions
    Demonstrates: Async processing, error handling, transaction management
    """
    from database import get_db_context
    
    logger.info(f"🔄 Processing upload {upload_id}")
    
    try:
        with get_db_context() as db:
            upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
            
            # Parse dates
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            else:
                df['timestamp'] = df['transaction_date']
            
            # Run ML categorization if category not in CSV
            if 'category' not in df.columns or df['category'].isna().any():
                logger.info("Running ML categorization...")
                categorizer = get_categorizer()
                predictions = categorizer.predict(df['clean_description'].fillna('').tolist())
                df['predicted_category'] = [p['category'] for p in predictions]
                df['prediction_confidence'] = [p['confidence'] for p in predictions]
                upload.categorization_completed = True
            
            # Run anomaly detection
            logger.info("Running anomaly detection...")
            detector = get_anomaly_detector()
            txn_dicts = df.to_dict('records')
            results = detector.detect_anomalies(txn_dicts)
            df_results = pd.DataFrame(results)
            
            # Merge results back
            for col in ['is_amount_anomaly', 'is_frequency_anomaly', 'is_merchant_anomaly', 'anomaly_score']:
                if col in df_results.columns:
                    df[col] = df_results[col]
            
            upload.anomaly_detection_completed = True
            
            # Save transactions to database
            logger.info("Saving to database...")
            transactions = []
            for _, row in df.iterrows():
                txn = Transaction(
                    transaction_id=row.get('transaction_id', f"txn_{uuid.uuid4().hex[:12]}"),
                    user_id=user_id,
                    upload_id=upload_id,
                    transaction_date=row['transaction_date'],
                    timestamp=row['timestamp'],
                    amount=float(row['amount']),
                    currency=row.get('currency', 'EUR'),
                    merchant=row['merchant'],
                    clean_description=str(row.get('clean_description', row['merchant'])),
                    category=row.get('category', row.get('predicted_category', 'Other')),
                    predicted_category=row.get('predicted_category'),
                    prediction_confidence=row.get('prediction_confidence'),
                    payment_method=row.get('payment_method'),
                    is_credit=bool(row.get('is_credit', False)),
                    hour_of_day=int(row.get('hour_of_day', 0)),
                    day_of_week=int(row.get('day_of_week', 0)),
                    is_weekend=bool(row.get('is_weekend', False)),
                    is_night=bool(row.get('is_night', False)),
                    is_amount_anomaly=bool(row.get('is_amount_anomaly', False)),
                    is_frequency_anomaly=bool(row.get('is_frequency_anomaly', False)),
                    is_merchant_anomaly=bool(row.get('is_merchant_anomaly', False)),
                    anomaly_score=float(row.get('anomaly_score', 0.0)),
                    processed_at=datetime.utcnow()
                )
                transactions.append(txn)
            
            db.bulk_save_objects(transactions)
            
            # Update upload status
            upload.status = 'completed'
            db.commit()
            
            logger.info(f"✅ Upload {upload_id} processed successfully")
            
    except Exception as e:
        logger.error(f"❌ Error processing upload {upload_id}: {str(e)}")
        
        with get_db_context() as db:
            upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
            if upload:
                upload.status = 'failed'
                upload.error_message = str(e)
                db.commit()