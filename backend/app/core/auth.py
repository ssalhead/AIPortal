"""
인증 및 권한 관리
개발 환경에서는 Mock 인증 사용
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.db.models.user import User
from app.repositories.user import UserRepository

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer 토큰 스키마
security = HTTPBearer(auto_error=False)


def create_access_token(data: Dict[str, Any]) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


class MockUser:
    """Mock 사용자 객체"""
    
    def __init__(self, user_id: str = None):
        self.id = UUID(user_id or settings.MOCK_USER_ID)  # Convert string to UUID
        self.email = settings.MOCK_USER_EMAIL
        self.username = settings.MOCK_USER_NAME
        self.full_name = settings.MOCK_USER_NAME
        self.is_active = True
        self.is_superuser = True
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """현재 인증된 사용자 조회"""
    
    # Mock 인증 모드
    if settings.MOCK_AUTH_ENABLED:
        return MockUser()
    
    # 실제 인증 모드
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    # 데이터베이스에서 사용자 조회
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    return user


async def get_current_user_with_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """현재 인증된 사용자 조회 (헤더 기반 Mock 인증 지원)"""
    
    # Mock 인증 모드
    if settings.MOCK_AUTH_ENABLED:
        # 헤더에서 사용자 ID 추출
        mock_user_id = request.headers.get("X-Mock-User-ID")
        if mock_user_id:
            try:
                # UUID 형식 검증
                UUID(mock_user_id)
                return MockUser(mock_user_id)
            except ValueError:
                pass  # 잘못된 UUID 형식이면 기본 사용자 사용
        
        # 기본 Mock 사용자 반환
        return MockUser()
    
    # 실제 인증 모드는 기존과 동일
    return await get_current_user(credentials, db)


async def get_current_active_user(
    current_user: User = Depends(get_current_user_with_header)
) -> User:
    """활성 사용자만 허용"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user_with_header)
) -> User:
    """관리자만 허용"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


class AuthService:
    """인증 서비스"""
    
    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession
    ) -> Optional[User]:
        """사용자 인증"""
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    @staticmethod
    async def register_user(
        email: str,
        username: str,
        password: str,
        full_name: Optional[str],
        db: AsyncSession
    ) -> User:
        """사용자 등록"""
        user_repo = UserRepository(db)
        
        # 중복 확인
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        existing_user = await user_repo.get_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # 사용자 생성
        hashed_password = get_password_hash(password)
        user = await user_repo.create_user(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name
        )
        
        return user