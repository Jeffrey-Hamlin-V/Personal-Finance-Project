"""
API Routes - FastAPI endpoints
Demonstrates: RESTful design, async processing, proper error handling
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import pandas as pd
import uuid
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db, Transaction, Upload, User, Insight
from api.schemas import (
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
                detail=f"Missing required columns: {missing}. Your CSV has: {list(df.columns)}"
            )
        
        # Check for duplicate transaction_ids within the CSV
        if 'transaction_id' in df.columns:
            duplicate_ids = df[df['transaction_id'].duplicated(keep=False)]
            if len(duplicate_ids) > 0:
                logger.warning(f"⚠️  Found {len(duplicate_ids)} duplicate transaction_ids in CSV. Keeping first occurrence.")
                # Remove duplicates, keeping first occurrence
                df = df.drop_duplicates(subset=['transaction_id'], keep='first')
                logger.info(f"📊 After removing duplicates: {len(df)} rows")
        
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
        progress_pct=progress,
        error_message=upload.error_message
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
    page_size: int = Query(50, ge=1, le=1000),  # Increased limit for dashboard needs
    db: Session = Depends(get_db)
):
    """
    Get transactions with filtering and pagination
    Demonstrates: Query optimization, pagination
    """
    
    try:
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
        
        # Validate transactions before returning
        valid_transactions = []
        for txn in transactions:
            try:
                # Ensure all required fields are present
                if txn.transaction_id and txn.merchant and txn.category:
                    valid_transactions.append(txn)
                else:
                    logger.warning(f"Skipping transaction {txn.id}: missing required fields")
            except Exception as e:
                logger.error(f"Error validating transaction {txn.id if hasattr(txn, 'id') else 'unknown'}: {str(e)}")
                continue
        
        return TransactionList(
            transactions=valid_transactions,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error fetching transactions for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")


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
    try:
        transactions = db.query(Transaction)\
                        .filter(Transaction.user_id == user_id)\
                        .all()
        
        if not transactions:
            logger.info(f"No transactions found for user {user_id}")
            raise HTTPException(status_code=404, detail="No transactions found for user. Please upload a CSV file first.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying transactions for dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard data: {str(e)}")
    
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
            
            # Parse dates with error handling
            try:
                df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
                invalid_dates = df['transaction_date'].isna().sum()
                if invalid_dates > 0:
                    logger.warning(f"Found {invalid_dates} invalid dates, setting to current date")
                    df.loc[df['transaction_date'].isna(), 'transaction_date'] = pd.Timestamp.now()
            except Exception as e:
                raise ValueError(f"Error parsing transaction_date column: {str(e)}")
            
            if 'timestamp' in df.columns:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    df.loc[df['timestamp'].isna(), 'timestamp'] = df['transaction_date']
                except Exception as e:
                    logger.warning(f"Error parsing timestamp, using transaction_date: {str(e)}")
                    df['timestamp'] = df['transaction_date']
            else:
                df['timestamp'] = df['transaction_date']
            
            # Run ML categorization if category not in CSV
            if 'category' not in df.columns or df['category'].isna().any():
                try:
                    logger.info("Running ML categorization...")
                    categorizer = get_categorizer()
                    predictions = categorizer.predict(df['clean_description'].fillna('').tolist())
                    df['predicted_category'] = [p['category'] for p in predictions]
                    df['prediction_confidence'] = [p['confidence'] for p in predictions]
                    upload.categorization_completed = True
                except Exception as e:
                    logger.warning(f"ML categorization failed: {str(e)}, using 'Other' as default")
                    df['predicted_category'] = 'Other'
                    df['prediction_confidence'] = 0.0
                    upload.categorization_completed = False
            
            # Run anomaly detection
            try:
                logger.info("Running anomaly detection...")
                detector = get_anomaly_detector()
                txn_dicts = df.to_dict('records')
                results = detector.detect_anomalies(txn_dicts)
                df_results = pd.DataFrame(results)
                
                # Merge results back
                for col in ['is_amount_anomaly', 'is_frequency_anomaly', 'is_merchant_anomaly', 'anomaly_score']:
                    if col in df_results.columns:
                        df[col] = df_results[col]
                    else:
                        # Set defaults if column missing
                        df[col] = False if 'anomaly' in col else 0.0
                
                upload.anomaly_detection_completed = True
            except Exception as e:
                logger.warning(f"Anomaly detection failed: {str(e)}, continuing without anomaly detection")
                df['is_amount_anomaly'] = False
                df['is_frequency_anomaly'] = False
                df['is_merchant_anomaly'] = False
                df['anomaly_score'] = 0.0
                upload.anomaly_detection_completed = False
            
            # Save transactions to database
            logger.info("Saving to database...")
            transactions = []
            errors = []
            skipped_duplicates = 0
            updated_existing = 0
            
            # Get existing transaction IDs for this user to avoid duplicates
            try:
                existing_txn_ids_result = db.scalars(
                    select(Transaction.transaction_id).where(Transaction.user_id == user_id)
                ).all()
                existing_txn_ids = set(existing_txn_ids_result) if existing_txn_ids_result else set()
                logger.info(f"📊 Found {len(existing_txn_ids)} existing transactions for user {user_id}")
            except Exception as e:
                logger.warning(f"⚠️  Error querying existing transactions: {str(e)}, proceeding without duplicate check")
                existing_txn_ids = set()
            
            for idx, row in df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row.get('amount')) or row.get('amount') == '':
                        errors.append(f"Row {idx}: Missing or invalid amount")
                        continue
                    
                    if pd.isna(row.get('merchant')) or str(row.get('merchant')).strip() == '':
                        errors.append(f"Row {idx}: Missing merchant name")
                        continue
                    
                    # Get transaction_id, generate if missing
                    txn_id = row.get('transaction_id')
                    if pd.isna(txn_id) or str(txn_id).strip() == '':
                        txn_id = f"txn_{uuid.uuid4().hex[:12]}"
                    else:
                        txn_id = str(txn_id).strip()
                    
                    # Check if transaction already exists
                    if txn_id in existing_txn_ids:
                        # Update existing transaction instead of creating duplicate
                        existing_txn = db.query(Transaction).filter(
                            Transaction.transaction_id == txn_id,
                            Transaction.user_id == user_id
                        ).first()
                        
                        if existing_txn:
                            # Update existing transaction with new data
                            existing_txn.upload_id = upload_id
                            existing_txn.transaction_date = row['transaction_date']
                            existing_txn.timestamp = row.get('timestamp', row['transaction_date'])
                            existing_txn.amount = float(row['amount'])
                            existing_txn.currency = row.get('currency', 'EUR')
                            existing_txn.merchant = str(row['merchant']).strip()
                            existing_txn.clean_description = str(row.get('clean_description', row['merchant'])).strip()
                            existing_txn.category = row.get('category') or row.get('predicted_category') or 'Other'
                            existing_txn.predicted_category = row.get('predicted_category') if pd.notna(row.get('predicted_category')) else None
                            existing_txn.prediction_confidence = float(row.get('prediction_confidence', 0.0)) if pd.notna(row.get('prediction_confidence')) else None
                            existing_txn.payment_method = row.get('payment_method')
                            existing_txn.is_credit = bool(row.get('is_credit', False))
                            existing_txn.hour_of_day = int(row.get('hour_of_day', 0)) if pd.notna(row.get('hour_of_day')) else 0
                            existing_txn.day_of_week = int(row.get('day_of_week', 0)) if pd.notna(row.get('day_of_week')) else 0
                            existing_txn.is_weekend = bool(row.get('is_weekend', False))
                            existing_txn.is_night = bool(row.get('is_night', False))
                            existing_txn.is_amount_anomaly = bool(row.get('is_amount_anomaly', False))
                            existing_txn.is_frequency_anomaly = bool(row.get('is_frequency_anomaly', False))
                            existing_txn.is_merchant_anomaly = bool(row.get('is_merchant_anomaly', False))
                            existing_txn.anomaly_score = float(row.get('anomaly_score', 0.0)) if pd.notna(row.get('anomaly_score')) else 0.0
                            existing_txn.processed_at = datetime.utcnow()
                            updated_existing += 1
                            continue
                        else:
                            # ID exists but not for this user - skip to avoid conflict
                            skipped_duplicates += 1
                            continue
                    
                    # Create new transaction
                    txn = Transaction(
                        transaction_id=txn_id,
                        user_id=user_id,
                        upload_id=upload_id,
                        transaction_date=row['transaction_date'],
                        timestamp=row.get('timestamp', row['transaction_date']),
                        amount=float(row['amount']),
                        currency=row.get('currency', 'EUR'),
                        merchant=str(row['merchant']).strip(),
                        clean_description=str(row.get('clean_description', row['merchant'])).strip(),
                        category=row.get('category') or row.get('predicted_category') or 'Other',
                        predicted_category=row.get('predicted_category') if pd.notna(row.get('predicted_category')) else None,
                        prediction_confidence=float(row.get('prediction_confidence', 0.0)) if pd.notna(row.get('prediction_confidence')) else None,
                        payment_method=row.get('payment_method'),
                        is_credit=bool(row.get('is_credit', False)),
                        hour_of_day=int(row.get('hour_of_day', 0)) if pd.notna(row.get('hour_of_day')) else 0,
                        day_of_week=int(row.get('day_of_week', 0)) if pd.notna(row.get('day_of_week')) else 0,
                        is_weekend=bool(row.get('is_weekend', False)),
                        is_night=bool(row.get('is_night', False)),
                        is_amount_anomaly=bool(row.get('is_amount_anomaly', False)),
                        is_frequency_anomaly=bool(row.get('is_frequency_anomaly', False)),
                        is_merchant_anomaly=bool(row.get('is_merchant_anomaly', False)),
                        anomaly_score=float(row.get('anomaly_score', 0.0)) if pd.notna(row.get('anomaly_score')) else 0.0,
                        processed_at=datetime.utcnow()
                    )
                    transactions.append(txn)
                    existing_txn_ids.add(txn_id)  # Track to avoid duplicates in same batch
                    
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
                    logger.warning(f"Error processing row {idx}: {str(e)}")
                    continue
            
            if errors and len(errors) > 10:
                error_summary = f"{len(errors)} rows had errors. First 10: {'; '.join(errors[:10])}"
                logger.warning(error_summary)
            elif errors:
                logger.warning(f"Errors in {len(errors)} rows: {'; '.join(errors)}")
            
            if skipped_duplicates > 0:
                logger.info(f"⏭️  Skipped {skipped_duplicates} duplicate transactions")
            
            if updated_existing > 0:
                logger.info(f"🔄 Updated {updated_existing} existing transactions")
            
            if not transactions and updated_existing == 0:
                raise ValueError(f"No new transactions to save. {skipped_duplicates} duplicates skipped. Check your CSV data format.")
            
            # Save new transactions in batches with error handling
            if transactions:
                try:
                    db.bulk_save_objects(transactions)
                    db.commit()
                    logger.info(f"✅ Saved {len(transactions)} new transactions, updated {updated_existing} existing")
                except IntegrityError as bulk_error:
                    # If bulk insert fails due to duplicates, try inserting one by one
                    logger.warning(f"⚠️  Bulk insert failed due to duplicate constraint: {str(bulk_error)}. Trying individual inserts...")
                    db.rollback()
                    
                    # Insert transactions one by one, skipping duplicates
                    saved_count = 0
                    for txn in transactions:
                        try:
                            # Check if it exists again (might have been added by another process)
                            exists = db.query(Transaction).filter(
                                Transaction.transaction_id == txn.transaction_id,
                                Transaction.user_id == user_id
                            ).first()
                            
                            if exists:
                                skipped_duplicates += 1
                                continue
                            
                            db.add(txn)
                            db.commit()
                            saved_count += 1
                        except IntegrityError as e:
                            db.rollback()
                            skipped_duplicates += 1
                            logger.warning(f"⚠️  Skipped duplicate transaction_id: {txn.transaction_id}")
                        except Exception as e:
                            db.rollback()
                            errors.append(f"Transaction {txn.transaction_id}: {str(e)}")
                            logger.error(f"❌ Error saving transaction {txn.transaction_id}: {str(e)}")
                    
                    logger.info(f"✅ Saved {saved_count} new transactions individually, skipped {skipped_duplicates} duplicates")
            else:
                # Commit updates even if no new transactions
                db.commit()
                logger.info(f"✅ Updated {updated_existing} existing transactions, no new transactions to add")
            
            # Verify transactions were saved
            final_count = db.query(Transaction).filter(Transaction.user_id == user_id).count()
            logger.info(f"📊 Total transactions for user {user_id} after upload: {final_count}")
            
            # Update upload status
            upload.status = 'completed'
            db.commit()
            
            logger.info(f"✅ Upload {upload_id} processed successfully")
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"{str(e)}\n\nTraceback:\n{error_trace}"
        logger.error(f"❌ Error processing upload {upload_id}: {error_msg}")
        
        with get_db_context() as db:
            upload = db.query(Upload).filter(Upload.upload_id == upload_id).first()
            if upload:
                upload.status = 'failed'
                # Store first 1000 chars of error (database limit)
                upload.error_message = error_msg[:1000] if len(error_msg) > 1000 else error_msg
                db.commit()