import os
from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "AI Forex Terminal"
    APP_VERSION: str = "1.0.0"
    PROJECT_NAME: str = "AI Forex Terminal"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api"
    
    # Auth & Security
    API_AUTH_TOKEN: str = "dev-secret-token"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./forex_terminal.db"
    
    # Market Data Integration (Twelve Data - Verified & Active)
    TWELVE_DATA_API_KEY: Optional[str] = None
    
    # AI Providers
    # PRIMARY: Gemini (verified active model: gemini-3.6-flash)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    
    # OPTIONAL FALLBACK: OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Risk & Safety Defaults
    DEFAULT_RISK_PER_TRADE: float = 0.01
    MAX_DAILY_DRAWDOWN: float = 0.05
    MAX_POSITION_SIZE_RATIO: float = 0.10
    
    # Upload Configuration
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"
    )

settings = Settings()
