import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for the EPFO Chatbot."""
    
    # App settings
    app_name: str = Field(default="Providentia - EPFO Bot Backend", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    version: str = Field(default="1.0.0", env="VERSION")
    
    # Supabase settings
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_role_key: str = Field(default="", env="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str = Field(default="", env="SUPABASE_JWT_SECRET")
    
    # Pinecone settings
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(..., env="PINECONE_INDEX_NAME")
    
    # AI/ML settings
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    huggingface_api_token: str = Field(default="", env="HUGGINGFACE_API_TOKEN")
    huggingface_model_url: str = Field(default="", env="HUGGINGFACE_MODEL_URL")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=10, env="RATE_LIMIT_PER_MINUTE")
    
    # CORS settings
    cors_origins: str = Field(default="http://localhost:3000", env="CORS_ORIGINS")
    
    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Convert comma-separated string to list of origins."""
        if not v:
            return ["*"]
        return [origin.strip() for origin in v.split(',') if origin.strip()]
    
    @field_validator('debug')
    @classmethod
    def parse_debug(cls, v) -> bool:
        """Parse debug value from string or bool."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)
    
    @property
    def get_pinecone_index(self) -> str:
        """Get pinecone index name from either variable."""
        return self.pinecone_index or self.pinecone_index_name or "default-index"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Ignore extra fields in .env file
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# For testing or dynamic reloading
def reload_settings() -> Settings:
    """Clear cache and reload settings."""
    get_settings.cache_clear()
    return get_settings()