"""
Anomaly Detection
Rule-based + statistical anomaly detection for transactions
"""

import numpy as np
import pandas as pd
from typing import List, Dict
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects anomalies in transactions using:
    - Statistical methods (Z-score)
    - Rule-based detection (duplicates, time-based)
    - Frequency analysis
    """
    
    def __init__(self, z_threshold: float = 3.0):
        """
        Initialize detector
        
        Args:
            z_threshold: Z-score threshold for amount anomalies
        """
        self.z_threshold = z_threshold
    
    def detect_anomalies(self, transactions: List[Dict]) -> List[Dict]:
        """
        Detect anomalies across multiple dimensions
        
        Args:
            transactions: List of transaction dicts with keys:
                - amount, category, merchant, is_weekend, is_night, transaction_date
        
        Returns:
            List of dicts with anomaly flags and scores
        """
        if not transactions:
            return []
        
        df = pd.DataFrame(transactions)
        
        # Initialize anomaly columns
        df['is_amount_anomaly'] = False
        df['is_frequency_anomaly'] = False
        df['is_merchant_anomaly'] = False
        df['anomaly_score'] = 0.0
        
        # 1. Amount-based anomalies (per category)
        df = self._detect_amount_anomalies(df)
        
        # 2. Frequency-based anomalies
        df = self._detect_frequency_anomalies(df)
        
        # 3. Time-based anomalies
        df = self._detect_time_anomalies(df)
        
        # 4. Duplicate detection
        df = self._detect_duplicates(df)
        
        # Calculate overall anomaly score (0-1)
        df['anomaly_score'] = (
            df['is_amount_anomaly'].astype(float) * 0.4 +
            df['is_frequency_anomaly'].astype(float) * 0.3 +
            df['is_merchant_anomaly'].astype(float) * 0.3
        )
        
        return df.to_dict('records')
    
    def _detect_amount_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect unusually high/low amounts per category using Z-score"""
        
        for category in df['category'].unique():
            mask = df['category'] == category
            amounts = df.loc[mask, 'amount']
            
            if len(amounts) < 3:  # Need at least 3 samples
                continue
            
            mean = amounts.mean()
            std = amounts.std()
            
            if std > 0:
                z_scores = np.abs((amounts - mean) / std)
                anomalies = z_scores > self.z_threshold
                df.loc[mask, 'is_amount_anomaly'] = anomalies
        
        return df
    
    def _detect_frequency_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect unusual frequency of transactions (same merchant, same day)"""
        
        if 'transaction_date' not in df.columns or 'merchant' not in df.columns:
            return df
        
        # Convert to date if datetime
        df['date'] = pd.to_datetime(df['transaction_date']).dt.date
        
        # Count transactions per merchant per day
        freq = df.groupby(['date', 'merchant']).size()
        
        # Flag if more than 3 transactions to same merchant in one day
        for (date, merchant), count in freq.items():
            if count > 3:
                mask = (df['date'] == date) & (df['merchant'] == merchant)
                df.loc[mask, 'is_frequency_anomaly'] = True
        
        df.drop('date', axis=1, inplace=True)
        return df
    
    def _detect_time_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Flag late-night/weekend transactions for certain categories"""
        
        # Categories that are unusual at night or weekends
        suspicious_night = ['Bills', 'Healthcare']
        
        if 'is_night' in df.columns:
            for category in suspicious_night:
                mask = (df['category'] == category) & (df['is_night'] == True)
                df.loc[mask, 'is_merchant_anomaly'] = True
        
        return df
    
    def _detect_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect potential duplicate charges (same merchant, amount, within 24h)"""
        
        if 'transaction_date' not in df.columns:
            return df
        
        df = df.sort_values('transaction_date')
        
        for i in range(len(df) - 1):
            current = df.iloc[i]
            next_txn = df.iloc[i + 1]
            
            # Check if same merchant and amount
            if (current['merchant'] == next_txn['merchant'] and 
                abs(current['amount'] - next_txn['amount']) < 0.01):
                
                # Check if within 24 hours
                time_diff = pd.to_datetime(next_txn['transaction_date']) - pd.to_datetime(current['transaction_date'])
                if time_diff.total_seconds() < 86400:  # 24 hours
                    df.loc[df.index[i + 1], 'is_frequency_anomaly'] = True
        
        return df
    
    def get_anomaly_summary(self, transactions: List[Dict]) -> Dict:
        """
        Get summary statistics of anomalies
        
        Returns:
            Dict with counts and percentages
        """
        results = self.detect_anomalies(transactions)
        df = pd.DataFrame(results)
        
        total = len(df)
        
        return {
            "total_transactions": total,
            "amount_anomalies": int(df['is_amount_anomaly'].sum()),
            "frequency_anomalies": int(df['is_frequency_anomaly'].sum()),
            "merchant_anomalies": int(df['is_merchant_anomaly'].sum()),
            "total_anomalies": int((df['anomaly_score'] > 0).sum()),
            "anomaly_rate": float((df['anomaly_score'] > 0).sum() / total) if total > 0 else 0
        }


# Global instance
_detector_instance = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get singleton detector instance"""
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
    
    return _detector_instance