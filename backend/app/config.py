"""
Application configuration settings
"""
import os
import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"

    # CORS Configuration
    # In production, set CORS_ORIGINS to your specific domain(s)
    # Example: CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATA_DIR: Path = BASE_DIR / "data"

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Gemini Configuration (for Target Analyzer)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Finnhub Configuration (for stock data)
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")

    # Tushare Configuration (for stock data - primary source for HK stocks)
    TUSHARE_API_TOKEN: str = os.getenv("TUSHARE_API_TOKEN", "")

    # Snowflake CapIQ Configuration (for premium company data)
    USE_CAPIQ_DATA: bool = os.getenv("USE_CAPIQ_DATA", "false").lower() == "true"
    SNOWFLAKE_USER: str = os.getenv("SNOWFLAKE_USER", "")
    SNOWFLAKE_PASSWORD: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    SNOWFLAKE_ACCOUNT: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    SNOWFLAKE_ROLE: str = os.getenv("SNOWFLAKE_ROLE", "")
    SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "")
    SNOWFLAKE_DATABASE: str = os.getenv("SNOWFLAKE_DATABASE", "CAPITAL_IQ")
    SNOWFLAKE_SCHEMA: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    # For key-pair authentication (alternative to password)
    SNOWFLAKE_PRIVATE_KEY_PATH: str = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "")
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE: str = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")

    # AWS Secrets Manager Configuration (alternative to direct API key)
    USE_AWS_SECRETS: bool = os.getenv("USE_AWS_SECRETS", "true").lower() == "true"
    AWS_SECRET_NAME_OPENAI: str = os.getenv("AWS_SECRET_NAME_OPENAI", "openai-api-key")
    AWS_SECRET_NAME_FINNHUB: str = os.getenv("AWS_SECRET_NAME_FINNHUB", "finnhub-api-key")
    AWS_SECRET_NAME_TUSHARE: str = os.getenv("AWS_SECRET_NAME_TUSHARE", "tushare-api-token")
    # Snowflake CapIQ credentials from AWS Secrets Manager
    AWS_SECRET_NAME_SNOWFLAKE_USER: str = os.getenv("AWS_SECRET_NAME_SNOWFLAKE_USER", "airflow/variables/CAPIQ_SNOWFLAKE_USER")
    AWS_SECRET_NAME_SNOWFLAKE_PASSWORD: str = os.getenv("AWS_SECRET_NAME_SNOWFLAKE_PASSWORD", "airflow/variables/CAPIQ_SNOWFLAKE_PASSWD")
    AWS_SECRET_NAME_SNOWFLAKE_ACCOUNT: str = os.getenv("AWS_SECRET_NAME_SNOWFLAKE_ACCOUNT", "airflow/variables/CAPIQ_SNOWFLAKE_ACCOUNT_ID")

    # Vision Model Configuration (for image processing in PDFs)
    VISION_MODEL: str = os.getenv("VISION_MODEL", "gpt-5.2")  # or "gpt-4o"

    # Answer Generation Model Configuration (for answering questions)
    ANSWER_MODEL: str = os.getenv("ANSWER_MODEL", "gpt-5.2")  # Model for generating answers (gpt-5.2, gpt-4.1, gpt-4o, o3, etc)
    ANSWER_TEMPERATURE: float = float(os.getenv("ANSWER_TEMPERATURE", "0"))

    # Online Search Model Configuration (for web search)
    ONLINE_SEARCH_MODEL: str = os.getenv("ONLINE_SEARCH_MODEL", "gpt-5.2")  # Model for online search (gpt-5.2, o3, etc)

    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-west-2")

    # S3 Storage Configuration
    USE_S3_STORAGE: bool = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
    AWS_S3_BUCKET: Optional[str] = os.getenv("AWS_S3_BUCKET")
    S3_UPLOAD_PREFIX: str = os.getenv("S3_UPLOAD_PREFIX", "uploads/")

    # AWS Athena Configuration (for IPO data)
    ATHENA_DATABASE: str = os.getenv("ATHENA_DATABASE", "capiq")
    ATHENA_OUTPUT_LOCATION: Optional[str] = os.getenv("ATHENA_OUTPUT_LOCATION")  # s3://bucket-name/athena-results/

    # Qdrant Configuration
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")

    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "Alibaba-NLP/gte-multilingual-base")

    # Document Processing
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    MAX_CONCURRENT_VISION_CALLS: int = int(os.getenv("MAX_CONCURRENT_VISION_CALLS", "10"))  # Max concurrent o4-mini API calls

    # Authentication
    # CRITICAL: Set SECRET_KEY environment variable in production!
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Security
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production

    # Rate Limiting
    # Format: "requests per time_period" (e.g., "10/minute", "100/hour", "1000/day")
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")  # General API endpoints
    RATE_LIMIT_SEARCH: str = os.getenv("RATE_LIMIT_SEARCH", "20/minute")  # AI search endpoints
    RATE_LIMIT_UPLOAD: str = os.getenv("RATE_LIMIT_UPLOAD", "10/minute")  # File upload endpoints
    RATE_LIMIT_AUTH: str = os.getenv("RATE_LIMIT_AUTH", "5/minute")  # Login/register endpoints

    # Supported file extensions
    SUPPORTED_EXTENSIONS: set = {
        ".pdf", ".txt", ".md", ".docx", ".doc",
        ".xlsx", ".xls", ".csv", ".pptx", ".ppt",
        ".html", ".htm", ".json", ".eml", ".zip"
    }

    class Config:
        case_sensitive = True
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Validate critical security settings in production
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY or self.SECRET_KEY == "change-this-in-production":
                raise ValueError(
                    "SECRET_KEY must be set in production! "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CORS_ORIGINS cannot contain '*' in production! "
                    "Set specific allowed origins in CORS_ORIGINS environment variable."
                )

        # Generate SECRET_KEY for development if not set
        if not self.SECRET_KEY:
            import secrets
            self.SECRET_KEY = secrets.token_urlsafe(32)
            logger.warning(
                "SECRET_KEY not set. Generated temporary key for development. "
                "Set SECRET_KEY environment variable for production!"
            )

        # Load API keys from AWS Secrets Manager if configured
        # Always load from Secrets Manager when USE_AWS_SECRETS=true, regardless of .env value
        if self.USE_AWS_SECRETS:
            self._load_openai_key_from_aws()
            self._load_finnhub_key_from_aws()
            self._load_tushare_token_from_aws()

    def _load_openai_key_from_aws(self):
        """Load OpenAI API key from AWS Secrets Manager"""
        try:
            from backend.app.utils.aws_secrets import get_key
            # Call exactly as user specified: get_key("openai-api-key", "us-west-2")
            self.OPENAI_API_KEY = get_key(
                self.AWS_SECRET_NAME_OPENAI,
                self.AWS_REGION
            )
            logger.info(f"Successfully loaded OpenAI API key from AWS Secrets Manager: {self.AWS_SECRET_NAME_OPENAI}")
        except Exception as e:
            logger.error(f"Failed to load OpenAI API key from AWS Secrets Manager: {str(e)}")
            raise

    def _load_finnhub_key_from_aws(self):
        """Load Finnhub API key from AWS Secrets Manager (optional - won't crash if fails)"""
        try:
            from backend.app.utils.aws_secrets import get_key
            self.FINNHUB_API_KEY = get_key(
                self.AWS_SECRET_NAME_FINNHUB,
                self.AWS_REGION
            )
            logger.info(f"Successfully loaded Finnhub API key from AWS Secrets Manager: {self.AWS_SECRET_NAME_FINNHUB}")
        except Exception as e:
            logger.warning(f"Could not load Finnhub API key from AWS Secrets Manager: {str(e)}")
            logger.warning("Stock tracker feature will not work without Finnhub API key")
            # Don't crash - just leave FINNHUB_API_KEY empty

    def _load_tushare_token_from_aws(self):
        """Load Tushare API token from AWS Secrets Manager (optional - won't crash if fails)"""
        # Only try AWS if token is not already set in environment
        if self.TUSHARE_API_TOKEN:
            logger.info(f"Tushare token already set from environment variable, skipping AWS Secrets Manager")
            return

        try:
            from backend.app.utils.aws_secrets import get_key
            self.TUSHARE_API_TOKEN = get_key(
                self.AWS_SECRET_NAME_TUSHARE,
                self.AWS_REGION
            )
            logger.info(f"Successfully loaded Tushare API token from AWS Secrets Manager: {self.AWS_SECRET_NAME_TUSHARE}")
        except Exception as e:
            logger.warning(f"Could not load Tushare API token from AWS Secrets Manager: {str(e)}")
            logger.warning("Will use fallback data sources for stock prices")
            # Don't crash - just leave TUSHARE_API_TOKEN empty

    def get_openai_api_key(self) -> str:
        """
        Get OpenAI API key from either environment variable or AWS Secrets Manager

        Returns:
            OpenAI API key

        Raises:
            ValueError: If API key is not configured
        """
        # Debug logging
        if self.OPENAI_API_KEY:
            masked = f"{self.OPENAI_API_KEY[:10]}...{self.OPENAI_API_KEY[-4:]}" if len(self.OPENAI_API_KEY) > 14 else "***"
            logger.info(f"get_openai_api_key() returning: {masked}")
        else:
            logger.warning("get_openai_api_key() called but OPENAI_API_KEY is empty!")

        if not self.OPENAI_API_KEY:
            if self.USE_AWS_SECRETS:
                logger.info("OPENAI_API_KEY is empty, loading from Secrets Manager...")
                self._load_openai_key_from_aws()
            else:
                raise ValueError(
                    "OpenAI API key not configured. "
                    "Set OPENAI_API_KEY in .env or enable USE_AWS_SECRETS=true"
                )
        return self.OPENAI_API_KEY

# Global settings instance
settings = Settings()
