"""
API 의존성 주입
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import verify_token, get_mock_user

# HTTP Bearer 토큰 스키마
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    현재 사용자 정보 반환
    
    Args:
        credentials: HTTP Bearer 토큰 자격증명
        
    Returns:
        사용자 정보 딕셔너리
        
    Raises:
        HTTPException: 인증 실패 시
    """
    # Mock 인증이 활성화된 경우
    if settings.MOCK_AUTH_ENABLED:
        mock_user = get_mock_user()
        if mock_user:
            return mock_user
    
    # 실제 토큰 검증 (Mock 인증이 비활성화된 경우)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_id = verify_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 실제 구현에서는 데이터베이스에서 사용자 정보를 조회
    # 현재는 토큰에 포함된 user_id만 반환
    return {
        "id": user_id,
        "is_active": True,
    }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    활성 사용자 정보 반환
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        활성 사용자 정보
        
    Raises:
        HTTPException: 비활성 사용자인 경우
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성 사용자입니다"
        )
    return current_user