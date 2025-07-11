from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Environment
    debug: bool = False
    env: str = "production"
    
    # LLM Configuration
    use_mock_llm: bool = False
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    
    # File Upload Configuration
    pdf_upload_max_size: int = 50000000  # 50MB
    pdf_upload_dir: str = "./uploads"
    pdf_storage_dir: str = "./storage"
    
    # OCR Configuration
    ocr_confidence_threshold: float = 0.9
    tesseract_config: str = "--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,()-:;/"
    
    # Processing Configuration
    max_pages_default: int = 10
    chunk_size_tokens: int = 4000
    chunk_overlap_tokens: int = 400
    processing_timeout: int = 300  # 5 minutes
    
    # Database Configuration
    database_url: str = "sqlite:///./document_analysis.db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str = "your_secret_key_here"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        os.makedirs(self.pdf_upload_dir, exist_ok=True)
        os.makedirs(self.pdf_storage_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    @property
    def available_llm_providers(self) -> List[str]:
        """Return list of available LLM providers based on configured API keys."""
        if self.use_mock_llm:
            return ["mock"]
        
        providers = []
        if self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
            providers.append("openai")
        if self.anthropic_api_key and self.anthropic_api_key != "your_anthropic_api_key_here":
            providers.append("anthropic")
        if self.deepseek_api_key and self.deepseek_api_key != "your_deepseek_api_key_here":
            providers.append("deepseek")
        
        # If no valid providers, fallback to mock mode
        if not providers:
            return ["mock"]
        
        return providers


# Global settings instance
settings = Settings()
