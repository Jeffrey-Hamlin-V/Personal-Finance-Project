"""
Insight Generation Engine
Generates natural language insights from transaction data
"""

import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InsightEngine:
    """Generates actionable insights from transaction data"""
    
    def generate_insights(self, transactions: List[Dict]) -> List[Dict]:
        """
        Generate insights from transactions
        
        Args:
            transactions: List of transaction dicts
        
        Returns:
            List of insight dicts with type, title, description
        """
        if not transactions:
            return []
        
        df = pd.DataFrame(transactions)
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        
        insights = []
        
        # 1. Spending summary by category
        insights.extend(self._category_spending_insights(df))
        
        # 2. Top merchants
        insights.extend(self._top_merchant_insights(df))
        
        # 3. Anomaly alerts
        insights.extend(self._anomaly_insights(df))
        
        # 4. Time-based patterns
        insights.extend(self._time_pattern_insights(df))
        
        return insights
    
    def _category_spending_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate insights about spending by category"""
        insights = []
        
        # Total spending by category
        category_totals = df[df['is_credit'] == False].groupby('category')['amount'].agg(['sum', 'count', 'mean'])
        category_totals = category_totals.sort_values('sum', ascending=False)
        
        total_spent = category_totals['sum'].sum()
        
        for category, row in category_totals.head(3).iterrows():
            pct = (row['sum'] / total_spent) * 100 if total_spent > 0 else 0
            
            insights.append({
                "type": "spending_summary",
                "title": f"{category} Spending",
                "description": (
                    f"You spent €{row['sum']:.2f} on {category} "
                    f"({pct:.0f}% of total spending) across {int(row['count'])} transactions. "
                    f"Average: €{row['mean']:.2f} per transaction."
                ),
                "category": category,
                "amount": float(row['sum']),
                "count": int(row['count'])
            })
        
        return insights
    
    def _top_merchant_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Identify top merchants"""
        insights = []
        
        merchant_totals = df[df['is_credit'] == False].groupby('merchant')['amount'].agg(['sum', 'count'])
        merchant_totals = merchant_totals.sort_values('sum', ascending=False)
        
        for merchant, row in merchant_totals.head(3).iterrows():
            insights.append({
                "type": "top_merchant",
                "title": f"Top Merchant: {merchant.title()}",
                "description": (
                    f"You spent €{row['sum']:.2f} at {merchant.title()} "
                    f"across {int(row['count'])} visits. "
                    f"Average: €{row['sum']/row['count']:.2f} per visit."
                ),
                "merchant": merchant,
                "amount": float(row['sum']),
                "count": int(row['count'])
            })
        
        return insights
    
    def _anomaly_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate alerts for detected anomalies"""
        insights = []
        
        # Amount anomalies
        if 'is_amount_anomaly' in df.columns:
            amount_anomalies = df[df['is_amount_anomaly'] == True]
            
            if len(amount_anomalies) > 0:
                for _, txn in amount_anomalies.head(3).iterrows():
                    insights.append({
                        "type": "anomaly_alert",
                        "title": "Unusual Amount Detected",
                        "description": (
                            f"Transaction of €{txn['amount']:.2f} at {txn['merchant'].title()} "
                            f"is significantly higher than your typical {txn['category']} spending."
                        ),
                        "severity": "high",
                        "transaction_id": txn.get('transaction_id')
                    })
        
        # Frequency anomalies
        if 'is_frequency_anomaly' in df.columns:
            freq_anomalies = df[df['is_frequency_anomaly'] == True]
            
            if len(freq_anomalies) > 0:
                # Group by merchant
                freq_by_merchant = freq_anomalies.groupby('merchant').size()
                
                for merchant, count in freq_by_merchant.head(2).items():
                    insights.append({
                        "type": "anomaly_alert",
                        "title": "Repeated Charges Detected",
                        "description": (
                            f"Multiple charges ({count}) from {merchant.title()} detected. "
                            f"Please verify these are not duplicates."
                        ),
                        "severity": "medium",
                        "merchant": merchant
                    })
        
        return insights
    
    def _time_pattern_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Identify spending patterns by time"""
        insights = []
        
        # Weekend vs weekday spending
        if 'is_weekend' in df.columns:
            weekend_spending = df[df['is_weekend'] == True]['amount'].sum()
            weekday_spending = df[df['is_weekend'] == False]['amount'].sum()
            
            weekend_days = df[df['is_weekend'] == True]['transaction_date'].dt.date.nunique()
            weekday_days = df[df['is_weekend'] == False]['transaction_date'].dt.date.nunique()
            
            if weekend_days > 0 and weekday_days > 0:
                weekend_avg = weekend_spending / weekend_days
                weekday_avg = weekday_spending / weekday_days
                
                if weekend_avg > weekday_avg * 1.2:
                    pct_more = ((weekend_avg / weekday_avg) - 1) * 100
                    insights.append({
                        "type": "trend",
                        "title": "Weekend Spending Pattern",
                        "description": (
                            f"You spend {pct_more:.0f}% more on weekends "
                            f"(€{weekend_avg:.2f}/day) compared to weekdays "
                            f"(€{weekday_avg:.2f}/day)."
                        )
                    })
        
        # Night spending
        if 'is_night' in df.columns:
            night_txns = df[df['is_night'] == True]
            
            if len(night_txns) > 5:
                night_spending = night_txns['amount'].sum()
                
                insights.append({
                    "type": "trend",
                    "title": "Late-Night Transactions",
                    "description": (
                        f"You made {len(night_txns)} transactions late at night (12am-6am), "
                        f"totaling €{night_spending:.2f}. Consider reviewing these for accuracy."
                    )
                })
        
        return insights
    
    def get_spending_summary(self, transactions: List[Dict]) -> Dict:
        """
        Get high-level spending summary
        
        Returns:
            Dict with total spend, income, categories, etc.
        """
        df = pd.DataFrame(transactions)
        
        # Separate credits (income) and debits (spending)
        credits = df[df['is_credit'] == True]['amount'].sum()
        debits = df[df['is_credit'] == False]['amount'].sum()
        
        # Category breakdown
        category_spending = df[df['is_credit'] == False].groupby('category')['amount'].sum().to_dict()
        
        return {
            "total_income": float(credits),
            "total_spending": float(debits),
            "net": float(credits - debits),
            "num_transactions": len(df),
            "category_breakdown": {k: float(v) for k, v in category_spending.items()},
            "avg_transaction": float(debits / len(df[df['is_credit'] == False])) if len(df[df['is_credit'] == False]) > 0 else 0
        }


# Global instance
_insight_engine_instance = None


def get_insight_engine() -> InsightEngine:
    """Get singleton insight engine instance"""
    global _insight_engine_instance
    
    if _insight_engine_instance is None:
        _insight_engine_instance = InsightEngine()
    
    return _insight_engine_instance