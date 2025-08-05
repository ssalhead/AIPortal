"""
보안 관련 유틸리티
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str | Any, expires_delta: Optional[timedelta] = None
) -> str:
    """
    액세스 토큰 생성
    
    Args:
        subject: 토큰 주제 (일반적으로 사용자 ID)
        expires_delta: 만료 시간 델타
    
    Returns:
        JWT 토큰 문자열
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    토큰 검증
    
    Args:
        token: JWT 토큰
    
    Returns:
        토큰 주제 (사용자 ID) 또는 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
    
    Returns:
        일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    비밀번호 해시 생성
    
    Args:
        password: 평문 비밀번호
    
    Returns:
        해시된 비밀번호
    """
    return pwd_context.hash(password)


# Mock 인증을 위한 가짜 사용자 정보
def get_mock_user() -> Dict[str, Any]:
    """
    Mock 사용자 정보 반환 (개발용)
    
    Returns:
        사용자 정보 딕셔너리
    """
    if settings.MOCK_AUTH_ENABLED:
        return {
            "id": settings.MOCK_USER_ID,
            "email": settings.MOCK_USER_EMAIL,
            "name": settings.MOCK_USER_NAME,
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow().isoformat(),
        }
    return None