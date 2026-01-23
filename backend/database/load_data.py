"""
Data Loader - Import cleaned CSV transactions into database
Matches the cleaned transaction CSV schema exactly
"""

import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import logging
import uuid

from .models import User, Transaction, Upload
from .init_db import get_db_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Handles bulk data import with proper error handling"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def load_transactions_from_csv(
        self, 
        csv_path: str, 
        user_id: str = "demo_user",
        batch_size: int = 500
    ) -> int:
        """
        Load transactions from cleaned CSV in batches
        
        Args:
            csv_path: Path to CSV file
            user_id: User ID to assign transactions to
            batch_size: Number of records per batch
        
        Returns:
            Number of transactions loaded
        """
        logger.info(f"📂 Loading transactions from {csv_path}")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Parse datetime columns
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create user if not exists
        self._create_user_if_not_exists(user_id)
        
        # Create upload record
        upload_id = f"upload_{uuid.uuid4().hex[:12]}"
        upload = Upload(
            upload_id=upload_id,
            user_id=user_id,
            filename=csv_path.split('/')[-1],
            num_transactions=len(df),
            status='processing'
        )
        self.db.add(upload)
        self.db.commit()
        
        total_loaded = 0
        
        # Process in batches
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            
            try:
                # Create transactions
                transactions = self._df_to_transactions(batch, user_id, upload_id)
                self.db.bulk_save_objects(transactions)
                self.db.commit()
                
                total_loaded += len(transactions)
                logger.info(f"✅ Loaded batch {i//batch_size + 1}: {len(transactions)} transactions")
                
            except Exception as e:
                self.db.rollback()
                logger.error(f"❌ Error loading batch {i//batch_size + 1}: {str(e)}")
                # Update upload status to failed
                upload.status = 'failed'
                upload.error_message = str(e)
                self.db.commit()
                raise
        
        # Update upload status to completed
        upload.status = 'completed'
        upload.categorization_completed = True  # CSV already has categories
        self.db.commit()
        
        logger.info(f"🎉 Total loaded: {total_loaded} transactions")
        return total_loaded
    
    def _create_user_if_not_exists(self, user_id: str):
        """Create user if not already in database"""
        existing = self.db.query(User).filter(User.user_id == user_id).first()
        if not existing:
            user = User(
                user_id=user_id,
                email=f"{user_id}@example.com"
            )
            self.db.add(user)
            self.db.flush()
    
    def _df_to_transactions(self, df: pd.DataFrame, user_id: str, upload_id: str) -> List[Transaction]:
        """Convert DataFrame rows to Transaction objects"""
        transactions = []
        
        for _, row in df.iterrows():
            txn = Transaction(
                transaction_id=row['transaction_id'],
                user_id=user_id,
                upload_id=upload_id,
                
                # Transaction details
                transaction_date=row['transaction_date'],
                timestamp=row['timestamp'],
                amount=float(row['amount']),
                currency=row['currency'],
                payment_method=row['payment_method'],
                is_credit=bool(row['is_credit']),
                
                # Merchant & description
                merchant=row['merchant'],
                clean_description=str(row['clean_description']) if pd.notna(row['clean_description']) else row['merchant'],
                
                # Category (ground truth from CSV)
                category=row['category'],
                
                # Time features
                hour_of_day=int(row['hour_of_day']),
                day_of_week=int(row['day_of_week']),
                is_weekend=bool(row['is_weekend']),
                is_night=bool(row['is_night']),
                
                # Anomaly flags
                is_amount_anomaly=bool(row['is_amount_anomaly']),
                is_frequency_anomaly=bool(row['is_frequency_anomaly']),
                is_merchant_anomaly=bool(row['is_merchant_anomaly']),
            )
            transactions.append(txn)
        
        return transactions


def load_sample_data(csv_path: str = "clean_transactions.csv", user_id: str = "demo_user"):
    """
    Convenience function to load sample data
    Usage: python -m backend.database.load_data
    """
    with get_db_context() as db:
        loader = DataLoader(db)
        count = loader.load_transactions_from_csv(csv_path, user_id=user_id)
        print(f"✅ Loaded {count} transactions for user '{user_id}'")


if __name__ == "__main__":
    # Initialize database first
    from .init_db import init_database
    init_database()
    
    # Load sample data
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "clean_transactions.csv"
    load_sample_data(csv_file)