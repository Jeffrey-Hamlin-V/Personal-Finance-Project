"""
Database Configuration
Demonstrates: Environment-based config, connection string management
"""

import os
from typing import Dict, Any


class DatabaseConfig:
    """Database configuration manager"""
    
    # Environment detection
    ENV = os.getenv("ENV", "development")
    
    # Database URLs by environment
    DATABASE_URLS = {
        "development": "sqlite:///./finance_intel.db",
        "testing": "sqlite:///./test_finance_intel.db",
        "production": os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/finance_intel")
    }
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL for current environment"""
        return cls.DATABASE_URLS.get(cls.ENV, cls.DATABASE_URLS["development"])
    
    @classmethod
    def get_pool_config(cls) -> Dict[str, Any]:
        """Get connection pool configuration"""
        if cls.ENV == "production":
            return {
                "pool_size": 20,
                "max_overflow": 40,
                "pool_timeout": 30,
                "pool_recycle": 3600,
            }
        else:
            return {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 10,
            }
    
    @classmethod
    def is_sqlite(cls) -> bool:
        """Check if using SQLite (affects query syntax)"""
        return cls.get_database_url().startswith("sqlite")


# Export configuration
config = DatabaseConfig()