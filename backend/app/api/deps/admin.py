"""
관리자 권한 확인 의존성 함수
"""

from typing import Dict, Any
from fastapi import HTTPException, status, Depends
from app.api.deps import get_current_active_user
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    현재 사용자가 관리자인지 확인
    
    Args:
        current_user: 현재 활성 사용자 정보
        
    Returns:
        관리자 사용자 정보
        
    Raises:
        HTTPException: 관리자가 아닌 경우 403 에러
    """
    
    try:
        # 사용자 권한 확인 (role 또는 is_admin 필드 확인)
        user_role = current_user.get('role', '').lower()
        is_admin = current_user.get('is_admin', False)
        
        # 관리자 권한 조건:
        # 1. role이 'admin'이거나
        # 2. is_admin이 True이거나  
        # 3. user_id가 시스템 관리자 ID인 경우 (임시)
        admin_conditions = [
            user_role == 'admin',
            is_admin is True,
            # 개발 환경에서 임시 관리자 권한 (실제 프로덕션에서는 제거 필요)
            str(current_user.get('id', '')).startswith('admin_'),
            current_user.get('email', '').endswith('@admin.com')
        ]
        
        if not any(admin_conditions):
            logger.warning(f"관리자 권한 접근 시도: user_id={current_user.get('id')}, role={user_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다."
            )
        
        logger.info(f"관리자 권한 확인 성공: user_id={current_user.get('id')}")
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 권한 확인 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="권한 확인 중 오류가 발생했습니다."
        )


def check_admin_permission(user_info: Dict[str, Any]) -> bool:
    """
    관리자 권한 확인 (동기 함수)
    
    Args:
        user_info: 사용자 정보
        
    Returns:
        관리자 여부
    """
    
    try:
        user_role = user_info.get('role', '').lower()
        is_admin = user_info.get('is_admin', False)
        
        admin_conditions = [
            user_role == 'admin',
            is_admin is True,
            str(user_info.get('id', '')).startswith('admin_'),
            user_info.get('email', '').endswith('@admin.com')
        ]
        
        return any(admin_conditions)
        
    except Exception as e:
        logger.error(f"관리자 권한 동기 확인 오류: {e}")
        return False


async def get_current_super_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    현재 사용자가 최고 관리자인지 확인
    
    Args:
        current_user: 현재 관리자 사용자 정보
        
    Returns:
        최고 관리자 사용자 정보
        
    Raises:
        HTTPException: 최고 관리자가 아닌 경우 403 에러
    """
    
    try:
        user_role = current_user.get('role', '').lower()
        
        # 최고 관리자 권한 조건
        super_admin_conditions = [
            user_role == 'super_admin',
            user_role == 'superadmin',
            current_user.get('is_super_admin', False),
            # 개발 환경 임시 조건
            str(current_user.get('id', '')).startswith('superadmin_')
        ]
        
        if not any(super_admin_conditions):
            logger.warning(f"최고 관리자 권한 접근 시도: user_id={current_user.get('id')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="최고 관리자 권한이 필요합니다."
            )
        
        logger.info(f"최고 관리자 권한 확인 성공: user_id={current_user.get('id')}")
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최고 관리자 권한 확인 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="권한 확인 중 오류가 발생했습니다."
        )