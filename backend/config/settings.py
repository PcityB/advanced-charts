from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://trading_user:trading_pass@localhost:5432/trading_simulator"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "trading_simulator"
    DATABASE_USER: str = "trading_user"
    DATABASE_PASSWORD: str = "trading_pass"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Data Import Settings
    DATA_DOWNLOAD_DIR: str = "./data/downloads"
    DATA_EXTRACTED_DIR: str = "./data/extracted"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
