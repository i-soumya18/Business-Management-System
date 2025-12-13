"""
Application Configuration
Using Pydantic Settings for environment variable management
"""
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Application Configuration
    APP_NAME: str = "Business Management System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    API_V1_PREFIX: str = "/api/v1"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = True
    
    # Database Configuration
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # MongoDB Configuration
    MONGODB_URL: str
    MONGODB_DATABASE: str = "bms_catalog"
    
    # Redis Configuration
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600
    REDIS_MAX_CONNECTIONS: int = 10
    
    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Configuration
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_HASH_ROUNDS: int = 12
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(default_factory=list)
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_HEADERS: List[str] = Field(default_factory=lambda: ["*"])
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    @validator("CORS_METHODS", pre=True)
    def parse_cors_methods(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    @validator("CORS_HEADERS", pre=True)
    def parse_cors_headers(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Email Configuration
    EMAIL_ENABLED: bool = True
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@yourbusiness.com"
    EMAIL_FROM_NAME: str = "Business Management System"
    
    # SMS Configuration
    SMS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # Payment Gateway - Stripe
    STRIPE_ENABLED: bool = True
    STRIPE_PUBLIC_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Payment Gateway - Razorpay
    RAZORPAY_ENABLED: bool = False
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    # File Storage
    USE_S3: bool = False
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET_NAME: Optional[str] = None
    AWS_S3_REGION: str = "us-east-1"
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # Celery Configuration
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = Field(default_factory=lambda: ["json"])
    CELERY_TIMEZONE: str = "UTC"
    
    @validator("CELERY_ACCEPT_CONTENT", pre=True)
    def parse_celery_accept_content(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    # ML/AI Configuration
    ML_ENABLED: bool = True
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    ML_MODEL_REGISTRY: str = "mlflow"
    ML_FORECAST_REFRESH_HOURS: int = 24
    
    # Elasticsearch Configuration
    ELASTICSEARCH_ENABLED: bool = False
    ELASTICSEARCH_URL: Optional[str] = None
    ELASTICSEARCH_INDEX_PREFIX: str = "bms"
    
    # Monitoring - Sentry
    SENTRY_ENABLED: bool = False
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/app.log"
    
    # Frontend URLs
    ADMIN_DASHBOARD_URL: str = "http://localhost:3000"
    STOREFRONT_URL: str = "http://localhost:3001"
    
    # Testing
    TEST_DATABASE_URL: Optional[str] = None
    
    # Feature Flags
    FEATURE_ML_FORECASTING: bool = True
    FEATURE_PRODUCT_RECOMMENDATIONS: bool = True
    FEATURE_DYNAMIC_PRICING: bool = False
    FEATURE_CHURN_PREDICTION: bool = False
    
    # Business Configuration
    COMPANY_NAME: str = "Your Company Name"
    COMPANY_CURRENCY: str = "USD"
    COMPANY_TIMEZONE: str = "UTC"
    TAX_RATE: float = 0.18
    
    # Inventory Configuration
    LOW_STOCK_THRESHOLD: int = 10
    CRITICAL_STOCK_THRESHOLD: int = 5
    
    # Order Configuration
    ORDER_AUTO_CANCEL_HOURS: int = 24
    ORDER_CONFIRMATION_REQUIRED: bool = True
    
    # Session Configuration
    SESSION_LIFETIME_HOURS: int = 24
    SESSION_CLEANUP_INTERVAL_HOURS: int = 6
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()


# Initialize Sentry if enabled
if settings.SENTRY_ENABLED and settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[FastApiIntegration()],
    )
