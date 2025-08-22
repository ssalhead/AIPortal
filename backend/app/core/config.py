"""
애플리케이션 설정 관리
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    PROJECT_NAME: str = "AI Portal"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API 설정
    API_V1_STR: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS 설정
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000"
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 데이터베이스 설정
    DATABASE_URL: Optional[str] = "postgresql+asyncpg://postgres:voA8NKk3DCQP6gQ6S5jO@10.130.5.114:5432/aiportal"
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    
    # AWS 설정
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-west-2"
    
    # DynamoDB 설정
    DYNAMODB_ENDPOINT: Optional[str] = "http://localhost:8000"
    DYNAMODB_TABLE_PREFIX: str = "ai_portal_"
    
    # OpenSearch 설정
    OPENSEARCH_URL: str = "http://localhost:9200"
    OPENSEARCH_USERNAME: Optional[str] = None
    OPENSEARCH_PASSWORD: Optional[str] = None
    OPENSEARCH_INDEX_PREFIX: str = "ai_portal_"
    
    # LLM API 키 (Claude via AWS Bedrock, Gemini via GCP)
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Google Custom Search 설정
    GOOGLE_CSE_ID: Optional[str] = None
    
    # 모니터링
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "ai-portal"
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Mock 인증 설정 (개발용)
    MOCK_AUTH_ENABLED: bool = True
    MOCK_USER_ID: str = "ff8e410a-53a4-4541-a7d4-ce265678d66a"  # 기존 DB의 사용자 ID
    MOCK_USER_EMAIL: str = "test@aiportal.com"  # 기존 이메일과 맞춤
    MOCK_USER_NAME: str = "테스트 사용자"
    
    # 파일 업로드 설정
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg"]
    UPLOAD_DIR: str = "uploads"
    
    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def assemble_allowed_extensions(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 디버그 로깅 설정 (환경변수로 제어)
    DEBUG_PERFORMANCE: bool = False
    DEBUG_STREAMING: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 설정 인스턴스 생성
settings = Settings()

# 초기화 직후 중요 설정값들 로깅
import logging
logger = logging.getLogger(__name__)

# Google API 설정 상태 확인 및 로깅
logger.info(f"=== 🔧 Google API 설정 상태 ===")
logger.info(f"GOOGLE_API_KEY: {'설정됨' if settings.GOOGLE_API_KEY else '설정되지 않음'}")
logger.info(f"GOOGLE_CSE_ID: {'설정됨' if settings.GOOGLE_CSE_ID else '설정되지 않음'}")
if settings.GOOGLE_API_KEY:
    logger.info(f"GOOGLE_API_KEY (앞 10자): {settings.GOOGLE_API_KEY[:10]}...")
if settings.GOOGLE_CSE_ID:
    logger.info(f"GOOGLE_CSE_ID: {settings.GOOGLE_CSE_ID}")
logger.info(f"===============================")