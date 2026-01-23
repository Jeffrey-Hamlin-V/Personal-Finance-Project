"""
Transaction Categorization Model
Loads trained TF-IDF + Logistic Regression model and runs inference
"""

import joblib
import logging
from typing import List, Tuple, Dict
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransactionCategorizer:
    """Wrapper for trained categorization model"""
    
    def __init__(self, model_path: str = "models/logreg_model.joblib"):
        """
        Load trained model
        
        Args:
            model_path: Path to saved model (.joblib file)
        """
        self.model_path = Path(model_path)
        self.model = None
        self.vectorizer = None
        self._load_model()
    
    def _load_model(self):
        """Load model and vectorizer from disk"""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. "
                f"Please train the model first using the ML training scripts."
            )
        
        logger.info(f"📦 Loading model from {self.model_path}")
        
        try:
            model_data = joblib.load(self.model_path)
            self.vectorizer = model_data["vectorizer"]
            self.model = model_data["model"]
            
            logger.info("✅ Model loaded successfully")
            logger.info(f"   Classes: {self.model.classes_}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {str(e)}")
            raise
    
    def predict(self, descriptions: List[str]) -> List[Dict[str, any]]:
        """
        Predict categories for transaction descriptions
        
        Args:
            descriptions: List of cleaned transaction descriptions
        
        Returns:
            List of dicts with 'category' and 'confidence'
        """
        if not descriptions:
            return []
        
        # Vectorize descriptions
        X = self.vectorizer.transform(descriptions)
        
        # Get predictions and probabilities
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)
        
        # Format results
        results = []
        for pred, proba in zip(predictions, probabilities):
            confidence = float(np.max(proba))
            results.append({
                "category": pred,
                "confidence": confidence,
                "probabilities": {
                    cls: float(prob) 
                    for cls, prob in zip(self.model.classes_, proba)
                }
            })
        
        return results
    
    def predict_single(self, description: str) -> Dict[str, any]:
        """
        Predict category for a single transaction
        
        Args:
            description: Cleaned transaction description
        
        Returns:
            Dict with 'category' and 'confidence'
        """
        results = self.predict([description])
        return results[0] if results else None
    
    def get_model_info(self) -> Dict[str, any]:
        """Get model metadata"""
        return {
            "model_type": "Logistic Regression",
            "vectorizer": "TF-IDF",
            "categories": list(self.model.classes_),
            "num_features": self.vectorizer.max_features,
            "model_path": str(self.model_path)
        }


# Global instance (lazy loaded)
_categorizer_instance = None


def get_categorizer(model_path: str = "models/logreg_model.joblib") -> TransactionCategorizer:
    """
    Get singleton categorizer instance
    Avoids loading model multiple times
    """
    global _categorizer_instance
    
    if _categorizer_instance is None:
        _categorizer_instance = TransactionCategorizer(model_path)
    
    return _categorizer_instance
    