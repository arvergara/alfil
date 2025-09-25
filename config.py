from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from typing import List, Dict, Optional
from datetime import time
import os
from pathlib import Path

class Settings(BaseSettings):
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    TEMPLATES_DIR: Path = PROJECT_ROOT / "templates"
    
    # Application settings
    APP_NAME: str = "ACAFI Clipping Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost/clipping_db",
        description="PostgreSQL connection string"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[SecretStr] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[SecretStr] = Field(default=None, env="ANTHROPIC_API_KEY")
    OLLAMA_URL: str = Field(default="http://localhost:11434", description="Ollama API URL")
    LLM_MODEL: str = Field(default="gpt-4-turbo-preview", description="Default LLM model")
    LLM_TEMPERATURE: float = Field(default=0.3, description="LLM temperature")
    LLM_MAX_TOKENS: int = Field(default=2000, description="Max tokens for LLM responses")
    
    # Mailchimp Configuration
    MAILCHIMP_API_KEY: Optional[SecretStr] = Field(default=None, env="MAILCHIMP_API_KEY")
    MAILCHIMP_SERVER_PREFIX: str = Field(default="us1", description="Mailchimp server prefix")
    MAILCHIMP_LIST_ID_ASOCIADOS: str = Field(default="", description="List ID for Asociados ACAFI")
    MAILCHIMP_LIST_ID_COLABORADORES: str = Field(default="", description="List ID for Colaboradores ACAFI")
    MAILCHIMP_TEMPLATE_ID: str = Field(default="", description="Template ID for newsletter")
    
    # Gmail Configuration (fallback)
    GMAIL_CREDENTIALS_FILE: Path = Field(default=PROJECT_ROOT / "credentials.json")
    GMAIL_TOKEN_FILE: Path = Field(default=PROJECT_ROOT / "token.json")
    GMAIL_SENDER_EMAIL: str = Field(default="acafi@acafi.com")
    
    # News Sources Configuration
    NEWS_SOURCES: List[Dict[str, str]] = Field(
        default=[
            {"name": "Diario Financiero", "url": "https://df.cl", "type": "web"},
            {"name": "El Mercurio", "url": "https://elmercurio.com", "type": "web"},
            {"name": "La Tercera", "url": "https://latercera.com", "type": "web"},
            {"name": "EMOL", "url": "https://emol.com", "type": "web"},
            {"name": "Funds Society", "url": "https://fundssociety.com", "type": "web"},
            {"name": "Banco Central", "url": "https://si3.bcentral.cl", "type": "api"},
        ]
    )
    
    # Scraping Configuration
    SCRAPING_TIMEOUT: int = Field(default=30, description="Timeout for web scraping in seconds")
    SCRAPING_MAX_RETRIES: int = Field(default=3, description="Max retries for failed requests")
    SCRAPING_DELAY: float = Field(default=1.0, description="Delay between requests in seconds")
    USE_PROXY: bool = Field(default=False, description="Use proxy for scraping")
    PROXY_URL: Optional[str] = Field(default=None, description="Proxy URL if USE_PROXY is True")
    
    # Newsletter Configuration
    NEWSLETTER_SEND_TIME: time = Field(default=time(8, 0), description="Daily send time")
    NEWSLETTER_TEST_EMAILS: List[str] = Field(
        default=["acafi@acafi.com", "btagle@proyectacomunicaciones.cl"],
        description="Test email recipients"
    )
    NEWSLETTER_MAX_ARTICLES_PER_SECTION: int = Field(default=10)
    NEWSLETTER_EDITORIAL_MAX_LINES: int = Field(default=6)
    
    # Keywords and Search Configuration
    KEYWORDS_FILE: Path = Field(
        default=Path("/Users/alfil/Library/CloudStorage/GoogleDrive-andres.vergara@maindset.cl/Mi unidad/0_Consultorias/Proyecta/Palabras_Claves.xlsx"),
        description="Path to keywords Excel file"
    )
    CLIENT_NAME: str = Field(default="ACAFI", description="Client name for keywords sheet")
    
    # Content Filtering
    DUPLICATE_THRESHOLD: float = Field(default=0.85, description="Similarity threshold for duplicates")
    MIN_ARTICLE_LENGTH: int = Field(default=100, description="Minimum article length in characters")
    MAX_ARTICLE_AGE_DAYS: int = Field(default=2, description="Maximum age of articles in days")
    
    # Monitoring and Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    
    # Scheduling
    ENABLE_SCHEDULER: bool = Field(default=True, description="Enable automatic scheduling")
    SCHEDULE_DAYS: List[str] = Field(
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        description="Days to run the newsletter"
    )
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = Field(default=900, description="Cache TTL in seconds (15 minutes)")
    ENABLE_CACHE: bool = Field(default=True, description="Enable caching")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Singleton instance
settings = Settings()

# Create necessary directories
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
